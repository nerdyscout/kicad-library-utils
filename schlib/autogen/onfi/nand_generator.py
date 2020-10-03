#!/usr/bin/env python3

import sys, os
import json, pyexcel
import flash_decoder
from csv import DictReader

sys.path.append(os.path.join(sys.path[0], '..'))
from KiCadSymbolGenerator import *

generator = SymbolGenerator('Memory_Flash_NAND')

def format(row):
    decode=flash_decoder.decode(row['part'])

    print(row['part'])
    if decode is not None:
        return {
            'part':row['part'],
            'vendor':row['vendor'] if row['vendor'] else decode['vendor'],
            'datasheet':row['datasheet'],
            'density':row['density'] if row['density'] else decode['density'],
            'width':row['width'] if row['width'] else decode['width'],
            'page_size':row['page_size'] if row['page_size'] else decode['page_size'],
            'page_size':'',
            'block_size':row['block_size'] if row['block_size'] else decode['block_size'],
            'block_size':'',
            'cells':row['cells'] if row['cells'] else decode['cells'],
            'voltage':json.loads(row['voltage']) if row['voltage'] else decode['voltage'],
            'classification':decode['classification'],
            'interface':decode['interface'],
            'footprint_default':row['footprint_default'] if row['footprint_default'] else decode['footprint_default'],
            'footprint_filters':row['footprint_filters'] if row['footprint_filters'] else decode['footprint_filters'],
            'temperature':row['temperature'] if row['temperature'] else decode['temperature'],
            'speed':row['speed'] if row['speed'] else decode['speed'],
            'alias':row['alias'] if row['alias'] else None
        }


def generateSymbol(flash):
    # get decoded values if no default in csv
    flash = format(flash)

    if flash is not None:
        # MODE
        if flash['interface']['async']:
            mode="DDR"
        elif flash['interface']['sync']:
            mode="SDR"
        else:
            return()

        # abort with invalid data
        if (flash['classification']['ce'] is None) or (flash['classification']['ch'] is None) or (mode is None):
            print ("flash not properly detected: " + str(flash))
            return()
        
        voltage=""
        if flash['voltage'] is not None:
            for key,value in flash['voltage'].items():
                if value:
                    voltage += key + ':' + str(value) +  ', '
        page_size = flash['page_size'] + ' Page, ' if flash['page_size'] else ''
        block_size = flash['block_size'] + ' Block, ' if flash['block_size'] else ''
        temperature = flash['temperature'] if flash['temperature'] else ''
        speed = flash['speed'] +', ' if flash['speed'] else ''
        keywords = str(voltage + page_size + block_size + speed).rstrip(',')
        description = flash['vendor'] + ' ' + flash['cells'] + ' NAND ' + flash['density'] + flash['width'] + ', ' + mode

        # symbol properties
        current_symbol = generator.addSymbol(flash['part'],
            dcm_options = {
                'datasheet': flash['datasheet'],
                'description': description,
                'keywords': keywords + temperature
            },num_units=flash['classification']['ch'])
        current_symbol.setReference('U', at={'x':0, 'y':100})
        current_symbol.setValue(at={'x':0, 'y':0})
        current_symbol.setDefaultFootprint (value=flash['footprint_default'], alignment_vertical=SymbolField.FieldAlignment.CENTER, visibility=SymbolField.FieldVisibility.INVISIBLE)

        # draw body
        for u in range (0,flash['classification']['ch']):
            rect = DrawingRectangle(start={'x':-700, 'y':1000}, end={'x':700, 'y':-1000}, fill=ElementFill.FILL_BACKGROUND,unit_idx=u)
            current_symbol.drawing.append(rect)

        # add pins
        current_symbol.pin_name_offset = 20
        package = pyexcel.get_sheet(file_name="pinmap.ods", name_columns_by_row=0, sheet_name=flash['footprint_default'].split(':')[1])
        for pin in package.to_records():
            if ((pin['interface'] == "") or (mode in pin['interface'].split(","))) and (pin['name']):
                if (int(pin['ce']) <= flash['classification']['ce']) and (pin['width']==flash['width'] or not pin['width']):
                    if pin['visibility'] == 'N':
                        vis=DrawingPin.PinVisibility('N')
                    else:
                        vis=DrawingPin.PinVisibility('')

                    current_symbol.drawing.append(DrawingPin(at=Point({'x':pin['x'], 'y':pin['y']},
                        grid=50), number=pin['pin'], name = pin['name'], orientation = DrawingPin.PinOrientation(pin['orientation']),
                        pin_length = 200, visibility=vis, el_type=DrawingPin.PinElectricalType(pin['type']),unit_idx=pin['channel']))

        # add alias
        if flash['alias']:
            for alias in json.loads(flash['alias']):
                current_symbol.addAlias(alias['part'], dcm_options={
                    'description': description,
                    'keywords': keywords + alias['temperature'],
                    'datasheet': alias['datasheet']}
                )

        # add footprint filters
        for filter in json.loads(flash['footprint_filters']):
            current_symbol.addFootprintFilter(filter)

    print('---')

if __name__ == '__main__':
    with open('flashes.csv', 'r') as read_obj:
        csv_dict_reader = DictReader(read_obj, delimiter=";")
        for row in csv_dict_reader:
           generateSymbol(row)

    generator.writeFiles()