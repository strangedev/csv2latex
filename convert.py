#!/bin/python3

import argparse
import csv
import locale
from math import log10, floor
from os import path
import yaml
import copy


parser = argparse.ArgumentParser(description='An utility for generating LaTeX tables from csv files')
parser.add_argument('file', type=str,
                    help='Path to the conversion description')
parser.add_argument('outpath', type=str, nargs='?',
                    help='Path to an output directory. If not passed,\
                          output is written to stdout.')
parser.add_argument('--encoding', type=str,
                    help='Optionally provide an encoding for\
                          the csv file, if the encoding is not\
                          utf-8')
parser.add_argument('--delimiter', type=str,
                    help='The csv delimiter char. Default: ;')
parser.add_argument('--quote-char', type=str,
                    help='The csv quote char. Default: "')
parser.add_argument('--skip-header', action='store_true',
                    help='Skip the first row of the csv files.')
parser.add_argument('--locale', type=str,
                    help='The locale that is used when converting\
                          numerical representations. Default: de_DE.UTF-8')


class ColumnDescription(object):

    def __init__(
        self,
        label='',
        numerical=True,
        significant_digits=3,
        convert=True,
        render=True
    ):
        self.label = label
        self.numerical = numerical
        self.significant_digits = significant_digits
        self.convert = convert
        self.render = render

    def __str__(self):
        return 'Column\n\
------\n\
Label: {}\n\
Numerical: {}\n\
Significant digits: {}\n\
Convert: {}\n\
Render: {}\n'.format(self.label,
                     self.numerical,
                     self.significant_digits,
                     self.convert,
                     self.render)


class TableDescription(object):

    def __init__(
        self,
        file_path,
        border=True,
        header_hline=True,
        row_hline=False,
        column_descriptions=None
    ):
        self.path = file_path
        self.border = border
        self.header_hline = header_hline
        self.row_hline = row_hline
        self.column_descriptions = column_descriptions or []

    def __str__(self):
        return "Table (@{}): {}\nColumns: {} (@{}) => {}".format(id(self), self.path, len(self.column_descriptions), id(self.column_descriptions), [c.label for c in self.column_descriptions])

    @property
    def col_count(self):
        return len(self.column_descriptions)

def round_sig(x, sig=2):
    if x == 0.0:
        return 0.0
    return round(x, sig-int(floor(log10(abs(x))))-1)

TABLE = '''
\\begin{{table}}[H]
    \centering
    \\begin{{tabular}}{{{columns_string}}}
        \hline
        {header_string}
        {rows}
        \hline
    \end{{tabular}}
    \caption{{{caption}}}
    \label{{table:{filename}}}
\end{{table}}
'''

def create_table(table_description, encoding, delimiter, quote_char, skip_header=False):
    with open(table_description.path, encoding=encoding, newline='') as f:
        reader = csv.reader(f, delimiter=delimiter, quotechar=quote_char)

        if skip_header:
            next(reader)

        col_count = 0
        for c in table_description.column_descriptions:
            if c.render:
                col_count += 1
        column_string = col_count * '|l' + '|'

        header_row = ""
        for c in table_description.column_descriptions:
            if not c.render:
                continue
            header_row += c.label + " & "
        header_row = header_row[:-2] + " \\\\ \n"
        if table_description.header_hline:
            header_row += '\t\hline'

        rows = ''
        row_i = 0
        for line in reader:
            row = '\t\t'
            col_i = 0
            for c in table_description.column_descriptions:
                try:
                    csv_val = line[col_i]
                except:
                    raise Exception("Column Nr. {} doesn't exist on line {} in file {}".format(col_i, row_i, table_description.path))


                if not c.render:
                    col_i += 1
                    continue
                if c.numerical:
                    if not csv_val:
                        csv_val = "0.0"
                    try:
                        csv_val = locale.atof(csv_val)
                        csv_val =  round_sig(csv_val, sig=c.significant_digits)
                    except Exception as e:
                        print("Offending value: {}".format(csv_val))
                        raise e 
                row += "{} & ".format(csv_val)
                col_i += 1
            row = row[:-2] + ' \\\\ \n'
            rows += row
            row_i += 1

        table  = TABLE.format(
            columns_string=column_string,
            header_string = header_row,
            rows=rows,
            caption=path.splitext(path.split(table_description.path)[1])[0].replace("_", " "),
            filename=path.split(table_description.path)[1]
            )

        return table

def parse_conversion_description(filepath):
    contents = None
    with open(filepath) as f:
        contents = yaml.load(f)

    workdir = contents['workdir']
    tables = contents['tables']
    
    table_descriptions = []
    for t in tables:
        for filename, params in t.items():
            print("[Parsing table] =>  {}".format(filename))
            td = TableDescription(path.join(workdir, filename))

            for column in params['columns']:
                #print("\t[Parsing Column] ->  {}".format(column))
                cd = ColumnDescription()

                for k, v in column.items():
                    #print("\t\t[Parsing Column Param] ~>  {}:{}".format(k,v))
                    setattr(cd, k, v)

                #print(id(td), [c.label for c in td.column_descriptions])
                td.column_descriptions.append(copy.deepcopy(cd))
                del cd

            table_descriptions.append(copy.deepcopy(td))
            del td
            continue
    
    return table_descriptions
                

def main(args):
    encoding = 'utf-8' if not args.encoding else args.encoding
    delimiter = ';' if not args.delimiter else args.delimiter
    quote_char = '"' if not args.quote_char else args.quote_char

    table_descriptions = parse_conversion_description(args.file)

    for td in table_descriptions:
        #print()
        #print(td)
        out = create_table(td, encoding, delimiter, quote_char, skip_header=args.skip_header)
        if args.outpath:
            filename = path.splitext(td.path)[0] + ".tex"
            outfile_path = path.join(args.outpath, filename)
            print("Writing to: {}".format(outfile_path))
            with open(outfile_path, 'w+') as f:
                f.write(out)
        else:
            print(out)

if __name__ == "__main__":
    args = parser.parse_args()
    locale_str = 'de_DE.UTF-8' if not args.locale else args.locale
    locale.setlocale(locale.LC_ALL, locale_str)
    main(args)
