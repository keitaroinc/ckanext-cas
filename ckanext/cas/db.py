import logging
import datetime
import sqlalchemy.exc
import ckan.plugins.toolkit as t

from ckan.model import domain_object
from ckan.model.meta import Session, metadata, mapper
from sqlalchemy import types, Column, Table, ForeignKey, func, CheckConstraint, UniqueConstraint

log = logging.getLogger(__name__)


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


cas_user_table = Table('ckanext_cas_login', metadata,
                       Column('ticket_id', types.UnicodeText, primary_key=True, nullable=False),
                       Column('user', types.UnicodeText, default=u'', nullable=False, unique=True),
                       Column('timestamp', types.DateTime, default=datetime.datetime.utcnow(), nullable=False))

mapper(CasUser, cas_user_table)


def create_cas_user_table():
    if not cas_user_table.exists():
        cas_user_table.create()


def insert_entry(ticket_id, user=None):
    create_cas_user_table()
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
    create_cas_user_table()
    cas_user_table.delete(CasUser.ticket_id == ticket_id).execute()


def delete_user_entry(user):
    cas_user_table.delete(CasUser.user == user).execute()


def is_ticket_valid(user):
    create_cas_user_table()
    search = {'user': user}
    results = CasUser.get(**search)
    log.info(results)
    if len(results) == 1:
        return True
    return False
