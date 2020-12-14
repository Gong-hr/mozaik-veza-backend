from django.core.management import BaseCommand

from mocbackend.databases import ElasticsearchDB
from mocbackend import models


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--init-entities', dest='init-entities', action='store_true')
        parser.add_argument('--init-attributes', dest='init-attributes', action='store_true')
        parser.add_argument('--init-connection-types', dest='init-connection-types', action='store_true')
        parser.add_argument('--init-attribute-values-log', dest='init-attribute-values-log', action='store_true')
        parser.add_argument('--init-entity-entity-log', dest='init-entity-entity-log', action='store_true')
        parser.add_argument('--init-codebook-values', dest='init-codebook-values', action='store_true')

        parser.add_argument('--overwrite', dest='overwrite', action='store_true')
        parser.add_argument('--queue', dest='queue', action='store_true')

        parser.add_argument('--offset', dest='offset', type=int)
        parser.add_argument('--limit', dest='limit', type=int)
        parser.add_argument('--chunk_size', dest='chunk_size', type=int)

        parser.add_argument('--entities', dest='entities', action='store_true')
        parser.add_argument('--entities-only_force_pep', dest='entities-only_force_pep', action='store_true')
        parser.add_argument('--entities-by_public_id', dest='entities-by_public_id')
        parser.add_argument('--entities-by_attribute', dest='entities-by_attribute')

        parser.add_argument('--attributes', dest='attributes', action='store_true')
        parser.add_argument('--connection-types', dest='connection-types', action='store_true')
        parser.add_argument('--attribute-values-log', dest='attribute-values-log', action='store_true')
        parser.add_argument('--entity-entity-log', dest='entity-entity-log', action='store_true')
        parser.add_argument('--codebook-values', dest='codebook-values', action='store_true')

    def handle(self, *args, **options):
        es_db = ElasticsearchDB.get_db()

        if options['init-entities']:
            es_db.init(command=self)

        if options['init-attributes']:
            es_db.init_attributes(command=self)

        if options['init-connection-types']:
            es_db.init_connection_types(command=self)

        if options['init-attribute-values-log']:
            es_db.init_attribute_values_log(command=self)

        if options['init-entity-entity-log']:
            es_db.init_entity_entity_log(command=self)

        if options['init-codebook-values']:
            es_db.init_codebook_values(command=self)

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
                        es_db.q_add_entity(entity=entity, overwrite=options['overwrite'], add_connections=True)
                    else:
                        es_db.add_entity(entity=entity, overwrite=options['overwrite'], add_connections=True)

                current_from = current_to

        if options['attributes']:
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

                attributes = models.StageAttribute.objects.filter(attribute=None).order_by('id')
                attributes = attributes[current_from:current_to]

                do_while = len(attributes) > 0

                self.stdout.write(
                    "Indexing " + str(len(attributes)) + " attributes (from " + str(current_from + 1) + " to " + str(
                        current_to) + ")...")
                for attribute in attributes:
                    if options['queue']:
                        es_db.q_add_attribute(attribute=attribute, overwrite=options['overwrite'])
                    else:
                        es_db.add_attribute(attribute=attribute, overwrite=options['overwrite'])

                current_from = current_to

        if options['connection-types']:
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

                connection_types = models.StaticConnectionType.objects.all().order_by('id')
                connection_types = connection_types[current_from:current_to]

                do_while = len(connection_types) > 0

                self.stdout.write("Indexing " + str(len(connection_types)) + " connection types (from " + str(
                    current_from + 1) + " to " + str(current_to) + ")...")
                for connection_type in connection_types:
                    if options['queue']:
                        es_db.q_add_connection_type(connection_type=connection_type, overwrite=options['overwrite'])
                    else:
                        es_db.add_connection_type(connection_type=connection_type, overwrite=options['overwrite'])

                current_from = current_to

        if options['attribute-values-log']:
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

                attribute_value_changes = models.LogAttributeValueChange.objects.all().order_by('id')
                attribute_value_changes = attribute_value_changes[current_from:current_to]

                do_while = len(attribute_value_changes) > 0

                self.stdout.write(
                    "Indexing " + str(len(attribute_value_changes)) + " attribute values changes (from " + str(
                        current_from + 1) + " to " + str(current_to) + ")...")
                for attribute_value_change in attribute_value_changes:
                    if options['queue']:
                        es_db.q_add_attribute_value_change(attribute_value_change=attribute_value_change,
                                                           overwrite=options['overwrite'])
                    else:
                        es_db.add_attribute_value_change(attribute_value_change=attribute_value_change,
                                                         overwrite=options['overwrite'])

                current_from = current_to

        if options['entity-entity-log']:
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

                entity_entity_changes = models.LogEntityEntityChange.objects.all().order_by('id')
                entity_entity_changes = entity_entity_changes[current_from:current_to]

                do_while = len(entity_entity_changes) > 0

                self.stdout.write("Indexing " + str(len(entity_entity_changes)) + " connection changes (from " + str(
                    current_from + 1) + " to " + str(current_to) + ")...")
                for entity_entity_change in entity_entity_changes:
                    if options['queue']:
                        es_db.q_add_entity_entity_change(entity_entity_change=entity_entity_change,
                                                         overwrite=options['overwrite'])
                    else:
                        es_db.add_entity_entity_change(entity_entity_change=entity_entity_change,
                                                       overwrite=options['overwrite'])

                current_from = current_to

        if options['codebook-values']:
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

                codebook_values = models.StageCodebookValue.objects.all().order_by('id')
                codebook_values = codebook_values[current_from:current_to]

                do_while = len(codebook_values) > 0

                self.stdout.write("Indexing " + str(len(codebook_values)) + " codebook values (from " + str(
                    current_from + 1) + " to " + str(current_to) + ")...")
                for codebook_value in codebook_values:
                    if options['queue']:
                        es_db.q_add_codebook_value(codebook_value=codebook_value, overwrite=options['overwrite'])
                    else:
                        es_db.add_codebook_value(codebook_value=codebook_value, overwrite=options['overwrite'])

                current_from = current_to

        self.stdout.write(self.style.SUCCESS('Finished!'))
