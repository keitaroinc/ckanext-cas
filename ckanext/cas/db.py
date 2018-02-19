import logging
import datetime
import sqlalchemy.exc
import ckan.plugins.toolkit as t

from ckan.model import domain_object
from ckan.model.meta import Session, metadata, mapper
from sqlalchemy.engine.reflection import Inspector
from sqlalchemy.exc import NoSuchTableError
from sqlalchemy import types, Column, Table, ForeignKey, func, CheckConstraint, UniqueConstraint, Index

log = logging.getLogger(__name__)

cas_table = None


def setup():
    if cas_table is None:
        define_cas_tables()
        log.debug('CAS table(s) defined in memory')

        if not cas_table.exists():
            cas_table.create()

    else:
        log.debug('CAS table(s) already exist')
        from ckan.model.meta import engine
        inspector = Inspector.from_engine(engine)

        try:
            inspector.get_indexes("ckanext_cas_login")
        except NoSuchTableError:
            cas_table.create()

        index_names = [index['name'] for index in inspector.get_indexes("ckanext_cas_login")]
        if not "ckanext_cas_login_ticket_id_idx" in index_names:
            log.debug('Creating index for ckanext_cas_login')
            Index("ckanext_cas_login_ticket_id_idx", cas_table.c.ticket_id).create()


class CasUser(domain_object.DomainObject):
    def __init__(self, ticket_id, user):
        self.ticket_id = ticket_id
        self.user = user

    @classmethod
    def get(cls, **kw):
        query = Session.query(cls).autoflush(False)
        return query.filter_by(**kw).all()

    @classmethod
    def delete(cls, **kw):
        query = Session.query(cls).autoflush(False).filter_by(**kw).all()
        for i in query:
            Session.delete(i)
        return


def define_cas_tables():
    global cas_table
    cas_table = Table('ckanext_cas_login', metadata,
                      Column('ticket_id', types.UnicodeText, primary_key=True, nullable=False),
                      Column('user', types.UnicodeText, default=u'', nullable=False, unique=True),
                      Column('timestamp', types.DateTime, default=datetime.datetime.utcnow(), nullable=False),
                      Index('ckanext_cas_login_ticket_id_idx', 'ticket_id'))

    mapper(
        CasUser,
        cas_table
    )


def insert_entry(ticket_id, user=None):
    try:
        if user is None:
            user = t.c.user
        cas_user = CasUser(ticket_id, user)
        cas_user.save()
        return True
    except sqlalchemy.exc.IntegrityError, exc:
        reason = exc.message
        log.error(reason)
        if reason.endswith('is not unique'):
            log.error('{0} already exists', exc.params[0])
        Session.rollback()
        return False
    except Exception:
        Session.rollback()
        return False


def delete_entry(ticket_id):
    cas_table.delete(CasUser.ticket_id == ticket_id).execute()


def delete_user_entry(user):
    cas_table.delete(CasUser.user == user).execute()


def is_ticket_valid(user):
    search = {'user': user}
    results = CasUser.get(**search)
    log.info(results)
    if len(results) == 1:
        return True
    return False
