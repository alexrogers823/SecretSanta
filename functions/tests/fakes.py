"""In-memory stand-ins for the parts of Firestore and Cloud Storage the functions use."""
import copy
from datetime import datetime, timezone

from firebase_admin import firestore
from google.api_core.exceptions import AlreadyExists, NotFound


def _resolve(value):
    if value is firestore.SERVER_TIMESTAMP:
        return datetime.now(timezone.utc)
    if isinstance(value, dict):
        return {key: _resolve(item) for key, item in value.items()}
    return value


class Snapshot:
    def __init__(self, reference, data):
        self.reference = reference
        self.id = reference.id
        self.exists = data is not None
        self._data = copy.deepcopy(data)

    def to_dict(self):
        return copy.deepcopy(self._data)

    def get(self, field):
        return self._data[field]


class DocumentRef:
    def __init__(self, db, path):
        self._db, self.path = db, path
        self.id = path.rsplit("/", 1)[-1]

    def collection(self, name):
        return CollectionRef(self._db, f"{self.path}/{name}")

    def get(self):
        return Snapshot(self, self._db.docs.get(self.path))

    def create(self, data):
        if self.path in self._db.docs:
            raise AlreadyExists(self.path)
        self._db.docs[self.path] = _resolve(data)

    def set(self, data, merge=False):
        data = _resolve(data)
        self._db.docs[self.path] = {**self._db.docs.get(self.path, {}), **data} if merge else data

    def update(self, data):
        if self.path not in self._db.docs:
            raise NotFound(self.path)
        self._db.docs[self.path].update(_resolve(data))

    def delete(self):
        self._db.docs.pop(self.path, None)


class CollectionRef:
    def __init__(self, db, path):
        self._db, self.path = db, path

    def document(self, doc_id):
        return DocumentRef(self._db, f"{self.path}/{doc_id}")

    def stream(self):
        depth = self.path.count("/") + 1
        for path in sorted(self._db.docs):
            if path.startswith(self.path + "/") and path.count("/") == depth:
                yield DocumentRef(self._db, path).get()


class Batch:
    def __init__(self):
        self._ops = []

    def create(self, ref, data):
        self._ops.append(lambda: ref.create(data))

    def set(self, ref, data, merge=False):
        self._ops.append(lambda: ref.set(data, merge=merge))

    def commit(self):
        for op in self._ops:
            op()


class FakeFirestore:
    def __init__(self):
        self.docs = {}  # "collection/doc/sub/doc" -> fields

    def collection(self, name):
        return CollectionRef(self, name)

    def batch(self):
        return Batch()

    # Test helpers
    def put(self, path, fields):
        self.docs[path] = copy.deepcopy(fields)

    def data(self, path):
        return self.docs.get(path)


class FakeBlob:
    def __init__(self, bucket, name):
        self._bucket, self.name = bucket, name
        self.cache_control = None

    def download_as_bytes(self):
        if self.name not in self._bucket.objects:
            raise NotFound(self.name)
        return self._bucket.objects[self.name]["data"]

    def upload_from_string(self, data, content_type=None):
        self._bucket.objects[self.name] = {"data": data, "content_type": content_type, "cache_control": self.cache_control}

    def delete(self):
        if self.name not in self._bucket.objects:
            raise NotFound(self.name)
        del self._bucket.objects[self.name]


class FakeBucket:
    def __init__(self, name):
        self.name = name
        self.objects = {}

    def blob(self, name):
        return FakeBlob(self, name)
