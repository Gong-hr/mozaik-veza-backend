import datetime

import django_rq
from django.core.cache import caches
from django.core.management import BaseCommand
from django.db.models import Q
from django.utils import timezone
from django.utils.timezone import localtime

from mocbackend import helpers, models
from mocbackend.databases import ElasticsearchDB, Neo4jDB


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--list', dest='list', action='store_true')
        parser.add_argument('--clear', dest='clear', action='store_true')
        parser.add_argument('--remove', dest='remove', type=str)
        parser.add_argument('--schedule', dest='schedule', type=str)
        parser.add_argument('--run', dest='run', type=str)
        parser.add_argument('--dry-run', dest='dry-run', action='store_true')
        parser.add_argument('--hours', dest='hours', type=int)
        parser.add_argument('--verbose', dest='verbose', action='store_true')

    def handle(self, *args, **options):
        if options['list']:
            scheduler = django_rq.get_scheduler('scheduler')
            jobs = scheduler.get_jobs(with_times=True)
            for job in jobs:
                print(job[0].id + ' ' + job[0].description + ' ' + str(job[1]))
        elif options['remove']:
            scheduler = django_rq.get_scheduler('scheduler')
            jobs = scheduler.get_jobs()
            for job in jobs:
                if job.id == options['remove']:
                    scheduler.cancel(job)
                    print('Job removed')
                    break
        elif options['clear']:
            scheduler = django_rq.get_scheduler('scheduler')
            jobs = scheduler.get_jobs()
            for job in jobs:
                scheduler.cancel(job=job)
                print('All jobs cleared')
        elif options['schedule']:
            job_func_name = None
            time = None
            if options['schedule'] == 'find_updated_entities_and_send_mail':
                job_func_name = 'mocbackend.management.commands.cron.find_updated_entities_and_send_mail'
                time = '0 17 * * 0'
            elif options['schedule'] == 'update_dbs':
                job_func_name = 'mocbackend.management.commands.cron.update'
                time = '0 */12 * * *'

            if job_func_name is None:
                print('Unknown job')
            else:
                scheduler = django_rq.get_scheduler('scheduler')
                jobs = scheduler.get_jobs()
                found = None
                for job in jobs:
                    if job.func_name == job_func_name:
                        found = job
                        break
                if found:
                    print('Job is already scheduled: ' + found.id)
                else:
                    scheduler.cron(
                        time,  # A cron string (e.g. "0 0 * * 0")
                        func=job_func_name,  # Function to be queued
                        repeat=None,  # Repeat this number of times (None means repeat forever)
                        queue_name='db'  # In which queue the job should be put in
                    )
                    print('Job scheduled')
        elif options['run']:
            if options['run'] == 'find_updated_entities_and_send_mail':
                find_updated_entities_and_send_mail(dry_run=options['dry-run'], verbose=options['verbose'])
            elif options['run'] == 'update_dbs':
                update(hours=options['hours'], dry_run=options['dry-run'], verbose=options['verbose'])


def find_updated_entities_and_send_mail(dry_run=False, verbose=False):
    users_to_send_mail = {}

    run_from = timezone.now() - datetime.timedelta(days=7)

    for entity in models.StageEntity.objects.filter(deleted=False, published=True, updated_at__gte=run_from):
        for watcher in entity.watchers.all():
            if watcher.send_notification_on_change_watched_entity and watcher.user.email is not None and watcher.user.email != '':
                tmp = users_to_send_mail.get(watcher.user.email, set())
                tmp.add(entity.public_id)
                users_to_send_mail.update({
                    watcher.user.email: tmp
                })

    queryset = models.StageAttributeValueCollection.objects.filter(Q(deleted=False,
                                                                     published=True,
                                                                     collection__deleted=False,
                                                                     collection__published=True,
                                                                     collection__source__deleted=False,
                                                                     collection__source__published=True,
                                                                     attribute_value__attribute__finally_deleted=False,
                                                                     attribute_value__attribute__finally_published=True) & (
                                                                           (~Q(attribute_value__entity=None) & Q(
                                                                               attribute_value__entity__deleted=False,
                                                                               attribute_value__entity__published=True)) | (
                                                                                   ~Q(
                                                                                       attribute_value__entity_entity=None) & Q(
                                                                               attribute_value__entity_entity__deleted=False,
                                                                               attribute_value__entity_entity__published=True,
                                                                               attribute_value__entity_entity__entity_a__deleted=False,
                                                                               attribute_value__entity_entity__entity_a__published=True,
                                                                               attribute_value__entity_entity__entity_b__deleted=False,
                                                                               attribute_value__entity_entity__entity_b__published=True,
                                                                               attribute_value__entity_entity__entity_entity_collections__deleted=False,
                                                                               attribute_value__entity_entity__entity_entity_collections__published=True,
                                                                               attribute_value__entity_entity__entity_entity_collections__collection__deleted=False,
                                                                               attribute_value__entity_entity__entity_entity_collections__collection__published=True,
                                                                               attribute_value__entity_entity__entity_entity_collections__collection__source__deleted=False,
                                                                               attribute_value__entity_entity__entity_entity_collections__collection__source__published=True))) & (
                                                                           Q(
                                                                               attribute_value__value_codebook_item=None) | Q(
                                                                       attribute_value__value_codebook_item__deleted=False,
                                                                       attribute_value__value_codebook_item__published=True,
                                                                       attribute_value__value_codebook_item__codebook__deleted=False,
                                                                       attribute_value__value_codebook_item__codebook__published=True)) & (
                                                                           Q(created_at__gte=run_from) | Q(
                                                                       updated_at__gte=run_from) | Q(
                                                                       attribute_value__created_at__gte=run_from) | Q(
                                                                       attribute_value__updated_at__gte=run_from))).distinct()
    for attribute_value_collection in queryset:
        if attribute_value_collection.attribute_value.entity is not None:
            entity = attribute_value_collection.attribute_value.entity
            for watcher in entity.watchers.all():
                if watcher.send_notification_on_change_watched_entity and watcher.user.email is not None and watcher.user.email != '':
                    tmp = users_to_send_mail.get(watcher.user.email, set())
                    tmp.add(entity.public_id)
                    users_to_send_mail.update({
                        watcher.user.email: tmp
                    })
        elif attribute_value_collection.attribute_value.entity_entity is not None:
            entity = attribute_value_collection.attribute_value.entity_entity.entity_a
            for watcher in entity.watchers.all():
                if watcher.send_notification_on_change_watched_entity and watcher.user.email is not None and watcher.user.email != '':
                    tmp = users_to_send_mail.get(watcher.user.email, set())
                    tmp.add(entity.public_id)
                    users_to_send_mail.update({
                        watcher.user.email: tmp
                    })
            entity = attribute_value_collection.attribute_value.entity_entity.entity_b
            for watcher in entity.watchers.all():
                if watcher.send_notification_on_change_watched_entity and watcher.user.email is not None and watcher.user.email != '':
                    tmp = users_to_send_mail.get(watcher.user.email, set())
                    tmp.add(entity.public_id)
                    users_to_send_mail.update({
                        watcher.user.email: tmp
                    })

    queryset = models.StageEntityEntityCollection.objects.filter(Q(deleted=False, published=True,
                                                                   collection__deleted=False,
                                                                   collection__published=True,
                                                                   collection__source__deleted=False,
                                                                   collection__source__published=True,
                                                                   entity_entity__deleted=False,
                                                                   entity_entity__published=True,
                                                                   entity_entity__entity_a__deleted=False,
                                                                   entity_entity__entity_a__published=True,
                                                                   entity_entity__entity_b__deleted=False,
                                                                   entity_entity__entity_b__published=True) & (
                                                                         Q(created_at__gte=run_from) | Q(
                                                                     updated_at__gte=run_from) | Q(
                                                                     entity_entity__created_at__gte=run_from) | Q(
                                                                     entity_entity__updated_at__gte=run_from)))
    for entity_entity_collection in queryset:
        entity = entity_entity_collection.entity_entity.entity_a
        for watcher in entity.watchers.all():
            if watcher.send_notification_on_change_watched_entity and watcher.user.email is not None and watcher.user.email != '':
                tmp = users_to_send_mail.get(watcher.user.email, set())
                tmp.add(entity.public_id)
                users_to_send_mail.update({
                    watcher.user.email: tmp
                })
        entity = entity_entity_collection.entity_entity.entity_b
        for watcher in entity.watchers.all():
            if watcher.send_notification_on_change_watched_entity and watcher.user.email is not None and watcher.user.email != '':
                tmp = users_to_send_mail.get(watcher.user.email, set())
                tmp.add(entity.public_id)
                users_to_send_mail.update({
                    watcher.user.email: tmp
                })

    if verbose:
        for email, public_ids in users_to_send_mail.items():
            print(email)
            for public_id in public_ids:
                print('  ' + public_id)

    if not dry_run:
        for email, public_ids in users_to_send_mail.items():
            helpers.send_mail_q(
                template_name='entity_change',
                from_email='kontakt@mozaikveza.hr',
                recipient_list=[email],
                context={
                    'public_ids': public_ids
                },
                fail_silently=False,
                queue_name='notification_mails'
            )


def update(hours=None, fallback_hours=12, dry_run=False, verbose=False):
    cache = caches['cron_update_dbs']
    update_dbs_running = cache.get('update_dbs_running')

    if dry_run:
        if update_dbs_running:
            print('Another update_dbs is running')
        print('Last run: ' + str(localtime(value=cache.get('update_dbs_last_run'))))

    if not update_dbs_running or dry_run:
        if not dry_run:
            cache.set('update_dbs_running', True, None)

        utcnow = timezone.now()

        if not hours:
            run_from = cache.get('update_dbs_last_run')
            if run_from is None:
                run_from = utcnow - datetime.timedelta(hours=fallback_hours)
        else:
            run_from = utcnow - datetime.timedelta(hours=hours)

        if not dry_run:
            cache.set('update_dbs_last_run', utcnow, None)

        entities_to_index_es = set()
        connections_to_index_es = set()

        entities_to_index_neo4j = set()
        connections_to_index_neo4j = set()

        for entity in models.StageEntity.objects.filter(
                Q(created_at__gte=run_from, created_at__lt=utcnow) | Q(updated_at__gte=run_from,
                                                                       updated_at__lt=utcnow)):
            entities_to_index_es.add(entity)
            entities_to_index_neo4j.add(entity)
            for entity_entity in models.StageEntityEntity.objects.filter(Q(entity_a=entity) | Q(entity_b=entity)).all():
                connections_to_index_es.add(entity_entity)

        for attribute_value_collection in models.StageAttributeValueCollection.objects.filter(
                Q(created_at__gte=run_from, created_at__lt=utcnow) | Q(
                    updated_at__gte=run_from, updated_at__lt=utcnow)):
            if attribute_value_collection.attribute_value.entity is not None:
                entities_to_index_es.add(attribute_value_collection.attribute_value.entity)
                if attribute_value_collection.attribute_value.attribute.string_id in ['person_first_name',
                                                                                      'person_last_name',
                                                                                      'legal_entity_name',
                                                                                      'legal_entity_entity_type',
                                                                                      'real_estate_name',
                                                                                      'movable_name',
                                                                                      'savings_name']:
                    entities_to_index_neo4j.add(attribute_value_collection.attribute_value.entity)
                    for entity_entity in models.StageEntityEntity.objects.filter(
                            Q(entity_a=attribute_value_collection.attribute_value.entity) | Q(
                                entity_b=attribute_value_collection.attribute_value.entity)).all():
                        connections_to_index_es.add(entity_entity)
            if attribute_value_collection.attribute_value.entity_entity is not None:
                connections_to_index_es.add(attribute_value_collection.attribute_value.entity_entity)

        for attribute_value in models.StageAttributeValue.objects.filter(
                Q(created_at__gte=run_from, created_at__lt=utcnow) | Q(
                    updated_at__gte=run_from, updated_at__lt=utcnow)):
            if attribute_value.entity is not None:
                entities_to_index_es.add(attribute_value.entity)
                if attribute_value.attribute.string_id in ['person_first_name', 'person_last_name', 'legal_entity_name',
                                                           'legal_entity_entity_type', 'real_estate_name',
                                                           'movable_name', 'savings_name']:
                    entities_to_index_neo4j.add(attribute_value.entity)
                    for entity_entity in models.StageEntityEntity.objects.filter(
                            Q(entity_a=attribute_value.entity) | Q(
                                entity_b=attribute_value.entity)).all():
                        connections_to_index_es.add(entity_entity)
            if attribute_value.entity_entity is not None:
                connections_to_index_es.add(attribute_value.entity_entity)

        for entity_entity_collection in models.StageEntityEntityCollection.objects.filter(
                Q(created_at__gte=run_from, created_at__lt=utcnow) | Q(
                    updated_at__gte=run_from, updated_at__lt=utcnow)):
            connections_to_index_es.add(entity_entity_collection.entity_entity)
            connections_to_index_neo4j.add(entity_entity_collection.entity_entity)

        for entity_entity in models.StageEntityEntity.objects.filter(
                Q(created_at__gte=run_from, created_at__lt=utcnow) | Q(
                    updated_at__gte=run_from, updated_at__lt=utcnow)):
            connections_to_index_es.add(entity_entity)
            connections_to_index_neo4j.add(entity_entity)

        if verbose:
            print('Elasticsearch entities:')
            for entity in entities_to_index_es:
                print(entity.entity_id)
            print('Elasticsearch connections:')
            for connection in connections_to_index_es:
                print(connection.id)

            print('Neo4j entities:')
            for entity in entities_to_index_neo4j:
                print(entity.entity_id)
            print('Neo4j connections:')
            for connection in connections_to_index_neo4j:
                print(connection.id)

        if not dry_run:
            es = ElasticsearchDB.get_db()
            for entity in entities_to_index_es:
                es.q_update_entity(entity=entity, update_connections=False)
            for connection in connections_to_index_es:
                es.q_update_connection(entity_entity=connection, calculate_count=True)

            neo4j = Neo4jDB.get_db()
            for entity in entities_to_index_neo4j:
                neo4j.q_update_entity(entity=entity, update_connections=False)
            for connection in connections_to_index_neo4j:
                neo4j.q_update_connection(entity_entity=connection)

        if not dry_run:
            cache.delete('update_dbs_running')
    elif update_dbs_running is not None:
        print('Another update_dbs is running.')
