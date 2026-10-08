from ..models import to_mapping_value
from ..storage.contracts import Conflict
from ..models import canonical_json
from .provenance import project_member, read_member, read_source

class WorkflowMembers:
    def __init__(self, store, objects):
        self.store, self.objects = store, objects

    def inventory(self):
        from ..models import Error
        valid, gaps = [], []
        for row in self.store.scan('WorkflowMember', {}):
            value = row.to_mapping()['value']
            try:
                read_member(value, self.store, self.objects)
                valid.append(value)
            except (ValueError, OSError, Conflict, KeyError, TypeError) as error:
                identity = value.get('member_id') if isinstance(value, dict) else None
                gaps.append(Error('legacy_member_unresolved', str(error), False, None,
                    {'record_kind': 'WorkflowMember', 'member_id': identity,
                     'record_sha256': __import__('hashlib').sha256(canonical_json(to_mapping_value(value))).hexdigest()}))
        return tuple(sorted(valid, key=lambda v: (v['source']['period'], v['source']['source_id'], v['member_id']))), tuple(gaps)

    def all(self):
        values, gaps = self.inventory()
        if gaps:
            raise Conflict('registry contains unresolved corrupt members')
        return values

    def register(self, parent_ref, member_ref):
        selected = read_source(member_ref, self.objects)
        if len(selected.members) != 1:
            raise Conflict('registry requires singleton member')
        value = project_member(parent_ref, selected.members[0].source_id, self.store, self.objects)
        if value['member_ref'] != member_ref:
            raise Conflict('registered member differs from exact projection')
        return value
