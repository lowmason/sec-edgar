"""Synthetic offline guard checks, not golden parser tests or live evidence."""
import io
import pathlib
import tempfile
import zipfile
import inspect_specimen as inspection


def archive_bytes(names):
    target = io.BytesIO()
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in names:
            archive.writestr(name, b'content')
    return target.getvalue()


with tempfile.TemporaryDirectory(dir='/private/tmp') as directory:
    scratch = pathlib.Path(directory)
    for names in (['../master.idx'], ['/master.idx'], ['master.idx', 'extra.txt']):
        source = scratch / 'source.zip'
        source.write_bytes(archive_bytes(names))
        try:
            inspection.inspect_archive(source, scratch)
        except ValueError:
            pass
        else:
            raise AssertionError(f'Unsafe archive accepted: {names}')
        assert not (scratch / 'master.idx').exists()
    source.write_bytes(archive_bytes(['master.idx']))
    saved_cap = inspection.EXPANSION_CAP
    inspection.EXPANSION_CAP = 2
    try:
        inspection.inspect_archive(source, scratch)
    except ValueError:
        pass
    else:
        raise AssertionError('Expansion limit ignored')
    finally:
        inspection.EXPANSION_CAP = saved_cap
    assert not (scratch / 'master.idx').exists()
    try:
        inspection.observe_text(b'\xff')
    except ValueError:
        pass
    else:
        raise AssertionError('Invalid selected decoding accepted')
print('PASS: synthetic traversal, absolute name, excess members, declared expansion cap, strict decoding rejection; no live source or production parser claims')
