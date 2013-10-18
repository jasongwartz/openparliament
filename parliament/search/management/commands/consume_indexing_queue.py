import itertools
import logging

from django.conf import settings
from django.core.management.base import BaseCommand

from haystack import site
import pysolr

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Runs any queued-up search indexing tasks."

    def handle(self, **options):

        from parliament.search.models import IndexingTask

        delete_tasks = list(
            IndexingTask.objects.filter(action='delete')
        )

        update_tasks = list(
            IndexingTask.objects.filter(action='update').prefetch_related('content_object')
        )

        solr = pysolr.Solr(settings.HAYSTACK_SOLR_URL, timeout=600)

        if update_tasks:
            update_objs = [t.content_object for t in update_tasks if t.content_object]

            update_objs.sort(key=lambda o: o.__class__.__name__)
            for cls, objs in itertools.groupby(update_objs, lambda o: o.__class__):
                logger.debug("Indexing %s" % cls)
                index = site.get_index(cls)
                prepared_objs = [index.prepare(o) for o in objs]
                solr.add(prepared_objs)

            IndexingTask.objects.filter(id__in=[t.id for t in update_tasks]).delete()

        if delete_tasks:
            for dt in delete_tasks:
                print "Deleting %s" % dt.identifier
                solr.delete(id=dt.identifier, commit=False)
            solr.commit()

            IndexingTask.objects.filter(id__in=[t.id for t in delete_tasks]).delete()




