from . import tradejournalutils as tju
import pytz
from datetime import datetime, timedelta
from azure.common import AzureMissingResourceHttpError
from werkzeug.utils import secure_filename
import uuid

class CommentMixin:
    def add_comment(self, key, comment_entity):
        """Add comments"""
        try:
            partition, row = tju.key_to_partition_and_row(key)
            add_time = str(pytz.UTC.localize(datetime.utcnow()).timestamp())
            comment_entity = dict(comment_entity)
            comment_entity.update(
            {
                'PartitionKey': key,
                'RowKey': add_time,
                'add_time' : add_time
            })
            self.svc.insert_entity(self.TABLES["comments"], comment_entity)
        except AzureMissingResourceHttpError:
            raise JournalEntryNotFound()

    def update_comment(self, comment_id, comment_entity):
        """Add comments"""
        try:
            partition, row = tju.key_to_partition_and_row(comment_id)
            comment_entity = dict(comment_entity)
            add_time = str(pytz.UTC.localize(datetime.utcnow()).timestamp())
            comment_entity.update(
            {
                'PartitionKey': partition,
                'RowKey': row,
                'add_time' : add_time
            })
            self.svc.update_entity(self.TABLES["comments"], comment_entity)
        except AzureMissingResourceHttpError:
            raise JournalEntryNotFound()
    
    def delete_comment(self, comment_id):
        """Add comments"""
        try:
            partition, row = tju.key_to_partition_and_row(comment_id)
            self.svc.delete_entity(self.TABLES["comments"], partition, row)
        except AzureMissingResourceHttpError:
            raise JournalEntryNotFound()

    def get_comments(self, key):
        """Returns all the comments from the repository."""
        partition, row = tju.key_to_partition_and_row(key)
        comment_entities = self.svc.query_entities(self.TABLES["comments"], "PartitionKey eq '%s'"%key)
        comments = [tju.comment_from_entity(entity) for entity in comment_entities]
        return comments

    def get_all_comments(self, forCount=False):
        """Returns all the comments from the repository."""
        if not forCount:
            comment_entities = self.svc.query_entities(self.TABLES["comments"])
        else:
            comment_entities = self.svc.query_entities(self.TABLES["comments"], select="PartitionKey")
        comments = [tju.comment_from_entity(entity) for entity in comment_entities]
        for comment in comments:
            try:
                comment.badge = self.GROUP_CACHE[comment.symbol].name
            except:
                try:
                    comment.badge = self.ENTRY_CACHE[comment.symbol].tradingsymbol
                except:
                    comment.badge = comment.symbol
        comments.sort(key = lambda x: x.add_time, reverse=True)
        return comments

    def get_all_comments_for_count(self):
        """Returns all the comments from the repository for counting"""
        lower_timestamp = pytz.UTC.localize(datetime.utcnow()) - timedelta(days=tju.ROLLING_AGE)
        query = "RowKey ge '%s'"%(str(lower_timestamp.timestamp()))
        comment_entities = self.svc.query_entities(self.TABLES["comments"], query, select="PartitionKey")
        return comment_entities

    def upload_image(self, upload):
        filename = secure_filename(upload.filename)
        blob_client = self.blob_service_client.get_blob_client(container="images", blob=filename)
        if blob_client.exists():
            filename, ext = filename.rsplit('.')
            filename = f"{filename}_{uuid.uuid1().hex}.{ext}"
            blob_client = self.blob_service_client.get_blob_client(container="images", blob=filename)
        blob_client.upload_blob(upload.stream.read(), overwrite=False)
        return filename

    def get_image(self, filename):
        blob_client = self.blob_service_client.get_blob_client(container="images", blob=filename)
        data = blob_client.download_blob().readall()
        return data
