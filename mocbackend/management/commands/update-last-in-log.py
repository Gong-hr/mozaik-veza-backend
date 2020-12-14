from django.core.management import BaseCommand
from mocbackend import models


class Command(BaseCommand):
    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        print('Collections', end='')
        for collection in models.StageCollection.objects.all():
            print('.', end='')
            latest = models.LogChangeset.objects.filter(deleted=False, published=True, collection=collection).order_by(
                '-created_at', '-id').first()

            collection.last_in_log = latest if latest is None else latest.created_at
            if collection.has_changed:
                collection.save()

        print('')
        print('Sources', end='')
        for source in models.StageSource.objects.all():
            print('.', end='')
            for collection in source.collections.filter(deleted=False, published=True):
                if collection.last_in_log is not None and (
                        source.last_in_log is None or collection.last_in_log > source.last_in_log):
                    source.last_in_log = collection.last_in_log

            if source.has_changed:
                source.save()

        print('')