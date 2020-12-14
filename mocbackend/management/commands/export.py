from django.core.management import BaseCommand

from elasticsearch import NotFoundError
from mocbackend.databases import ElasticsearchDB
import json

from mocbackend import const


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('--type', dest='type')
        parser.add_argument('--id', dest='id')

    def handle(self, *args, **options):
        if options['type'] is not None and (options['type'] == 'entity' or options['type'] == 'connections') and \
                options['id'] is not None:
            if options['type'] == 'entity':
                if ElasticsearchDB.is_elasticsearch_settings_exists():
                    pk = options['id']
                    es = ElasticsearchDB.get_db().get_elasticsearch()
                    try:
                        result_raw = es.get(index=ElasticsearchDB.get_elasticsearch_index_name(
                            const.ELASTICSEARCH_ENTITIES_INDEX_NAME),
                            doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), id=pk)

                        result = result_raw['_source']
                        result.update({
                            'public_id': result_raw['_id']
                        })
                        with open('entity_%s.json' % pk, 'w') as fp:
                            try:
                                json.dump(result, fp)
                                self.stdout.write(self.style.SUCCESS('Finished!'))
                            except Exception:
                                self.stdout.write(self.style.ERROR('Error in saving to file!'))
                    except NotFoundError:
                        self.stdout.write(self.style.ERROR('Not found!'))
                else:
                    self.stdout.write(self.style.ERROR('Elasticsearch not configured!'))
            elif options['type'] == 'connections':
                pk = options['id']
                body = {
                    'query': {
                        'bool': {
                            'should': [
                                {
                                    'term': {
                                        'entity_a.public_id': pk
                                    }
                                },
                                {
                                    'term': {
                                        'entity_b.public_id': pk
                                    }
                                }
                            ]
                        }
                    }
                }
                if ElasticsearchDB.is_elasticsearch_settings_exists():
                    es = ElasticsearchDB.get_db().get_elasticsearch()
                    results_raw = es.search(
                        index=ElasticsearchDB.get_elasticsearch_index_name(const.ELASTICSEARCH_CONNECTIONS_INDEX_NAME),
                        doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), body=body)
                    hits = results_raw['hits']
                    results = []
                    for hit in hits['hits']:
                        source = hit['_source']
                        source.update({
                            'id': hit['_id']
                        })
                        results.append(source)
                    with open('connections_%s.json' % pk, 'w') as fp:
                        try:
                            json.dump(results, fp)
                            self.stdout.write(self.style.SUCCESS('Finished!'))
                        except Exception:
                            self.stdout.write(self.style.ERROR('Error in saving to file!'))
                else:
                    self.stdout.write(self.style.ERROR('Elasticsearch not configured!'))
        else:
            self.stdout.write('Syntax: python manage.py export --type <entity|connections> --id <id>')
