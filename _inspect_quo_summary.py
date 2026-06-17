import zipfile
import xml.etree.ElementTree as ET

NS = {
    'a': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
}


def get_text_from_si(si):
    return ''.join(node.text or '' for node in si.iter('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t'))

with zipfile.ZipFile(r'static\media\quo.xlsx') as archive:
    sst = []
    try:
        root = ET.fromstring(archive.read('xl/sharedStrings.xml'))
        sst = [get_text_from_si(si) for si in root.findall('a:si', NS)]
    except KeyError:
        pass

    workbook = ET.fromstring(archive.read('xl/workbook.xml'))
    sheets = workbook.find('a:sheets', NS)
    rels = ET.fromstring(archive.read('xl/_rels/workbook.xml.rels'))
    rel_map = {rel.attrib['Id']: rel.attrib['Target'] for rel in rels}
    first_sheet = sheets[0]
    target = rel_map[first_sheet.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']]
    sheet = ET.fromstring(archive.read('xl/' + target))

    print('SHEET', first_sheet.attrib['name'])
    dim = sheet.find('a:dimension', NS)
    print('DIM', dim.attrib.get('ref') if dim is not None else '')

    merges = sheet.find('a:mergeCells', NS)
    if merges is not None:
        print('MERGES')
        for m in merges:
            print(' ', m.attrib['ref'])

    cols = sheet.find('a:cols', NS)
    if cols is not None:
        print('COLS')
        for col in cols.findall('a:col', NS):
            print(' ', dict(col.attrib))

    print('ROWS')
    for row in sheet.findall('.//a:sheetData/a:row', NS):
        rnum = int(row.attrib['r'])
        out = []
        for c in row.findall('a:c', NS):
            ref = c.attrib.get('r')
            t = c.attrib.get('t')
            s = c.attrib.get('s')
            v = c.find('a:v', NS)
            is_node = c.find('a:is', NS)
            value = ''
            if t == 's' and v is not None:
                value = sst[int(v.text)]
            elif t == 'inlineStr' and is_node is not None:
                value = ''.join(node.text or '' for node in is_node.iter('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t'))
            elif v is not None:
                value = v.text or ''
            if value or s not in (None, '0'):
                out.append(f'{ref} [s={s}]: {value}')
        if out:
            print(f'ROW {rnum}')
            for item in out:
                print(' ', item)
