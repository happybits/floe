import boto3
from botocore.exceptions import ClientError
from .helpers import validate_key


class DynamoFloe(object):
    """
    An implementation of cold storage in dynamodb.
    """
    def __init__(self, table, initialize=False, **conn_kwargs):
        self.table_name = table
        self.dynamodb = boto3.resource('dynamodb', **conn_kwargs)
        if initialize:
            self.create_floe_table()
        self.table = self.dynamodb.Table(self.table_name)

    def create_floe_table(self):
        """
        Takes in the table_name but hard-codes the rest so we can create
        temporary testing tables in different
        namespaces without having to know about internal structure.
        :param table_name: DDB Table Name
        :return: the raw API response.
        """
        try:
            return self.dynamodb.create_table(
                TableName=self.table_name,
                KeySchema=[
                    {
                        'AttributeName': 'key',
                        'KeyType': 'HASH'
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'key',
                        'AttributeType': 'S'
                    }
                ],
                ProvisionedThroughput={
                    'ReadCapacityUnits': 10,
                    'WriteCapacityUnits': 10
                }
            )
        except ClientError:
            pass

    def delete_floe_table(self):
        self.table.delete()

    def get(self, key):
        """
        get the value of a given key
        :param pk:
        :return:
        """
        validate_key(key)
        response = self.table.get_item(
            Key={
                'key': key
            }
        )
        if 'Item' not in response:
            return None
        item = response['Item']
        return None if 'value' not in item else item['value']

    def get_multi(self, keys):
        """
        get the values for a list of keys as a dictionary.
        keys that are not found will be missing from the response.
        :param keys:
        :return:
        """
        # TODO: use batch_get_item for performance
        if not keys:
            return {}
        for key in keys:
            validate_key(key)

        result = {k: self.get(k) for k in keys}
        return {k: v for k, v in result.items() if v is not None}

    def set(self, key, bin_data):
        """
        set a given key
        :param key:
        :param bin_data:
        :return:
        """
        validate_key(key)
        self.table.put_item(
            Item={
                'key': key,
                'value': boto3.dynamodb.types.Binary(bin_data)
            }
        )

    def set_multi(self, mapping):
        """
        set a series of keys based on the dictionary passed in
        :param mapping: dict
        :return:
        """
        # TODO: use batch_write_item for performance
        for key in mapping.keys():
            validate_key(key)
        for k, v in mapping.items():
            self.set(k, v)

    def delete(self, key):
        """
        delete a given key
        :param key:
        :return:
        """
        validate_key(key)

        self.table.delete_item(
            Key={
                'key': key
            }
        )

    def delete_multi(self, keys):
        """
        delete a set of given keys
        :param keys:
        :return:
        """
        for key in keys:
            validate_key(key)

        # no batch delete API in Dynamo, so we loop through singles,
        # could expand to launch threads/gevent
        for key in keys:
            self.delete(key)

    def ids(self):
        """
        return a generator that iterates through all ids in cold storage
        no particular order. useful for a script to crawl through stuff that
        has been frozen and thaw it.
            :return:
        """
        start_key = None
        while True:
            response = self.table.scan(ExclusiveStartKey=start_key) \
                if start_key else self.table.scan()
            for item in response['Items']:
                yield item['key']

            if 'LastEvaluatedKey' not in response:
                break
            start_key = response['LastEvaluatedKey']

    def flush(self):
        self.delete_floe_table()
        self.create_floe_table()
