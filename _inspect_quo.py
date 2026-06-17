import json
import zipfile
import xml.etree.ElementTree as ET

NS = {
    'a': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
}


def load_shared_strings(archive):
    try:
        root = ET.fromstring(archive.read('xl/sharedStrings.xml'))
    except KeyError:
        return []
    values = []
    for si in root.findall('a:si', NS):
        texts = [node.text or '' for node in si.iter('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t')]
        values.append(''.join(texts))
    return values


def parse_styles(archive):
    styles = ET.fromstring(archive.read('xl/styles.xml'))
    fills = styles.find('a:fills', NS)
    fonts = styles.find('a:fonts', NS)
    cell_xfs = styles.find('a:cellXfs', NS)
    return fills, fonts, cell_xfs


def cell_style_summary(style_idx, fills, fonts, cell_xfs):
    if style_idx is None:
        return {}
    idx = int(style_idx)
    if idx >= len(cell_xfs):
        return {'style': idx}
    xf = cell_xfs[idx]
    font_id = int(xf.attrib.get('fontId', 0))
    fill_id = int(xf.attrib.get('fillId', 0))
    summary = {
        'style': idx,
        'fontId': font_id,
        'fillId': fill_id,
        'numFmtId': xf.attrib.get('numFmtId'),
    }
    if fill_id < len(fills):
        fill = fills[fill_id]
        pat = fill.find('a:patternFill', NS)
        if pat is not None:
            fg = pat.find('a:fgColor', NS)
            bg = pat.find('a:bgColor', NS)
            summary['patternType'] = pat.attrib.get('patternType')
            summary['fgColor'] = fg.attrib if fg is not None else None
            summary['bgColor'] = bg.attrib if bg is not None else None
    if font_id < len(fonts):
        font = fonts[font_id]
        color = font.find('a:color', NS)
        size = font.find('a:sz', NS)
        name = font.find('a:name', NS)
        summary['fontColor'] = color.attrib if color is not None else None
        summary['fontSize'] = size.attrib.get('val') if size is not None else None
        summary['fontName'] = name.attrib.get('val') if name is not None else None
        summary['bold'] = font.find('a:b', NS) is not None
        summary['italic'] = font.find('a:i', NS) is not None
    return summary


def cell_value(cell, shared_strings):
    cell_type = cell.attrib.get('t')
    value = cell.find('a:v', NS)
    inline = cell.find('a:is', NS)
    if cell_type == 's' and value is not None:
        index = int(value.text)
        return shared_strings[index] if index < len(shared_strings) else ''
    if cell_type == 'inlineStr' and inline is not None:
        return ''.join(node.text or '' for node in inline.iter('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t'))
    if value is not None:
        return value.text or ''
    return ''


with zipfile.ZipFile(r'static\media\quo.xlsx') as archive:
    workbook = ET.fromstring(archive.read('xl/workbook.xml'))
    sheets = workbook.find('a:sheets', NS)
    rels = ET.fromstring(archive.read('xl/_rels/workbook.xml.rels'))
    rel_map = {rel.attrib['Id']: rel.attrib['Target'] for rel in rels}
    sheet_names = [sheet.attrib['name'] for sheet in sheets]
    first_sheet = sheets[0]
    target = rel_map[first_sheet.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']]

    shared_strings = load_shared_strings(archive)
    fills, fonts, cell_xfs = parse_styles(archive)
    sheet = ET.fromstring(archive.read('xl/' + target))

    dimension = sheet.find('a:dimension', NS)
    merges = sheet.find('a:mergeCells', NS)
    cols = sheet.find('a:cols', NS)

    result = {
        'sheet_names': sheet_names,
        'first_sheet': first_sheet.attrib['name'],
        'dimension': dimension.attrib if dimension is not None else {},
        'merges': [m.attrib['ref'] for m in merges] if merges is not None else [],
        'cols': [c.attrib for c in cols.findall('a:col', NS)] if cols is not None else [],
        'rows': [],
    }

    for row in sheet.findall('.//a:sheetData/a:row', NS):
        row_num = int(row.attrib['r'])
        if row_num > 45:
            break
        row_data = {'row': row_num, 'cells': []}
        for cell in row.findall('a:c', NS):
            row_data['cells'].append(
                {
                    'ref': cell.attrib.get('r'),
                    'value': cell_value(cell, shared_strings),
                    'style': cell_style_summary(cell.attrib.get('s'), fills, fonts, cell_xfs),
                }
            )
        result['rows'].append(row_data)

print(json.dumps(result, ensure_ascii=False, indent=2))
