from django.core.management import BaseCommand
from neo4j.v1 import GraphDatabase

from mocbackend import models
from mocbackend.databases import Neo4jDB


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--init-entities', dest='init-entities', action='store_true')

        parser.add_argument('--overwrite', dest='overwrite', action='store_true')
        parser.add_argument('--queue', dest='queue', action='store_true')

        parser.add_argument('--offset', dest='offset', type=int)
        parser.add_argument('--limit', dest='limit', type=int)
        parser.add_argument('--chunk_size', dest='chunk_size', type=int)

        parser.add_argument('--entities', dest='entities', action='store_true')
        parser.add_argument('--entities-only_force_pep', dest='entities-only_force_pep', action='store_true')
        parser.add_argument('--entities-by_public_id', dest='entities-by_public_id')
        parser.add_argument('--entities-by_attribute', dest='entities-by_attribute')

    def handle(self, *args, **options):
        neo4j_db = Neo4jDB.get_db()

        if options['init-entities']:
            neo4j_db.init(command=self)

        if options['entities']:
            current_from = options['offset'] if options['offset'] is not None else 0
            chunk_size = options['chunk_size'] if options['chunk_size'] is not None else 10000

            total_to = None
            if options['limit'] is not None:
                total_to = current_from + options['limit']

            do_while = True
            while do_while and (total_to is None or (current_from < total_to)):
                current_to = current_from + chunk_size
                if total_to is not None and current_to > total_to:
                    current_to = total_to

                entities = models.StageEntity.objects.all().order_by('id')

                if options['entities-only_force_pep']:
                    entities = entities.filter(force_pep=True)

                if options['entities-by_public_id'] is not None and options['entities-by_public_id'] != '':
                    entities = entities.filter(public_id=options['entities-by_public_id'])
                elif options['entities-by_attribute'] is not None and options['entities-by_attribute'] != '':
                    entities = entities.filter(
                        attribute_values__attribute__string_id=options['entities-by_attribute']).distinct()

                entities = entities[current_from:current_to]

                do_while = len(entities) > 0

                self.stdout.write(
                    "Indexing " + str(len(entities)) + " entities (from " + str(current_from + 1) + " to " + str(
                        current_to) + ")...")
                for entity in entities:
                    if options['queue']:
                        neo4j_db.q_add_entity(entity=entity, overwrite=options['overwrite'], add_connections=True)
                    else:
                        neo4j_db.add_entity(entity=entity, overwrite=options['overwrite'], add_connections=True)

                current_from = current_to

        self.stdout.write(self.style.SUCCESS('Finished!'))
