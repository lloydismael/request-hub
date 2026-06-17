import zipfile
import xml.etree.ElementTree as ET

NS = {'a': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
STYLE_IDS = {1,2,3,5,6,7,8,9,10,11,12,13,15,17,18,19,20,21,22,24,25,26,28,29,31,32,33,34,35,36,38,39,40,42}

with zipfile.ZipFile(r'static\media\quo.xlsx') as archive:
    styles = ET.fromstring(archive.read('xl/styles.xml'))
    fills = styles.find('a:fills', NS)
    fonts = styles.find('a:fonts', NS)
    borders = styles.find('a:borders', NS)
    cell_xfs = styles.find('a:cellXfs', NS)

    for idx, xf in enumerate(cell_xfs):
        if idx not in STYLE_IDS:
            continue
        font_id = int(xf.attrib.get('fontId', 0))
        fill_id = int(xf.attrib.get('fillId', 0))
        border_id = int(xf.attrib.get('borderId', 0))
        print(f'STYLE {idx}')
        print(' xf', dict(xf.attrib))
        if font_id < len(fonts):
            font = fonts[font_id]
            print(' font', {
                'name': (font.find('a:name', NS).attrib.get('val') if font.find('a:name', NS) is not None else None),
                'size': (font.find('a:sz', NS).attrib.get('val') if font.find('a:sz', NS) is not None else None),
                'bold': font.find('a:b', NS) is not None,
                'italic': font.find('a:i', NS) is not None,
                'color': (font.find('a:color', NS).attrib if font.find('a:color', NS) is not None else None),
            })
        if fill_id < len(fills):
            fill = fills[fill_id]
            pat = fill.find('a:patternFill', NS)
            print(' fill', {
                'patternType': pat.attrib.get('patternType') if pat is not None else None,
                'fgColor': (pat.find('a:fgColor', NS).attrib if pat is not None and pat.find('a:fgColor', NS) is not None else None),
                'bgColor': (pat.find('a:bgColor', NS).attrib if pat is not None and pat.find('a:bgColor', NS) is not None else None),
            })
        if border_id < len(borders):
            border = borders[border_id]
            border_summary = {}
            for side in ['left', 'right', 'top', 'bottom']:
                node = border.find(f'a:{side}', NS)
                if node is not None and node.attrib:
                    border_summary[side] = dict(node.attrib)
            print(' border', border_summary)
        print()
