# -*- coding: utf-8 -*-
from plone.app.discussion.interfaces import IComment
from plone.app.discussion.interfaces import IConversation
from plone.restapi.batching import HypermediaBatch
from plone.restapi.interfaces import IJsonCompatible
from plone.restapi.interfaces import ISerializeToJson
from plone.restapi.services.discussion.utils import can_delete
from plone.restapi.services.discussion.utils import can_delete_own
from plone.restapi.services.discussion.utils import can_edit
from plone.restapi.services.discussion.utils import delete_own_comment_allowed
from plone.restapi.services.discussion.utils import edit_comment_allowed
from zope.component import adapter
from zope.component import getMultiAdapter
from zope.interface import implementer
from zope.publisher.interfaces import IRequest


@implementer(ISerializeToJson)
@adapter(IConversation, IRequest)
class ConversationSerializer(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self):
        # We'll batch the threads
        results = list(self.context.getThreads())
        batch = HypermediaBatch(self.request, results)

        results = {}
        results['@id'] = batch.canonical_url

        results['items_total'] = batch.items_total
        if batch.links:
            results['batching'] = batch.links

        results['items'] = [
            getMultiAdapter(
                (thread['comment'], self.request),
                ISerializeToJson
            )()
            for thread in batch
        ]

        return results


@implementer(ISerializeToJson)
@adapter(IComment, IRequest)
class CommentSerializer(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self):
        content_url = self.context.__parent__.__parent__.absolute_url()
        comments_url = '{}/@comments'.format(content_url)
        url = '{}/{}'.format(comments_url, self.context.id)

        if self.context.in_reply_to:
            parent_url = '{}/{}'.format(
                comments_url, self.context.in_reply_to
            )
            in_reply_to = str(self.context.in_reply_to)
        else:
            parent_url = None
            in_reply_to = None

        doc_allowed = delete_own_comment_allowed()
        delete_own = doc_allowed and can_delete_own(self.context)

        return {
            '@id': url,
            '@type': self.context.portal_type,
            '@parent': parent_url,
            'comment_id': str(self.context.id),
            'in_reply_to': in_reply_to,
            'text': {
                'data': self.context.text,
                'mime-type': self.context.mime_type
            },
            'user_notification': self.context.user_notification,
            'author_username': self.context.author_username,
            'author_name': self.context.author_name,
            'creation_date': IJsonCompatible(self.context.creation_date),
            'modification_date': IJsonCompatible(self.context.modification_date),  # noqa
            'is_editable': edit_comment_allowed() and can_edit(self.context),
            'is_deletable': can_delete(self.context) or delete_own
        }
