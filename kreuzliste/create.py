import codecs
from datetime import date
import os
import random
import re
from string import Template
import subprocess
import sys
import yaml


def run_pdflatex(path_to_file, filename):
    args = ["pdflatex", "--interaction=nonstopmode", filename]
    with open(os.devnull, 'w') as FNULL:
        res = subprocess.run(args, cwd=path_to_file, stdout=FNULL).returncode
    return res


def make_main_file(single_sheets, data):
    context = {}
    context["language"] = data["language"]
    context["includes"] = "\n\n\\clearpage\n\n".join(single_sheets)
    return Template(data["main_file_template"]).substitute(context)


def make_single_sheet(group, users, data):
    offsets = calc_offsets(users, data["rows"], data["whitespace"], data["rowHeight"])
    context = {}
    context["title"] = group
    context["datestamp"] = date.today().isoformat()
    context["creator_id"] = data["creator_id"]
    context["quote"] = random.choice(data["quotes"])
    context["contents"] = ", ".join((
        create_tikz_contents(data["offset"] - offsets[i], u, data["rows"], data["columns"], data["rowHeight"])
        for i, u in enumerate(users)
        ))
    context["whitespace"] = data["whitespace"]
    context["rowHeight"] = data["rowHeight"]
    context["cellWidth"] = data["cellWidth"]
    return Template(data["single_sheet_template"]).substitute(context)

def calc_offsets(users, default_rows, whitespace, row_height):
    offsets = []
    offset = 0
    for i, u in enumerate(users):
        cur_offset = whitespace + row_height * (u["rows"] if "rows" in u else default_rows)
        offset += cur_offset
        offsets.append(offset)
    return offsets

def create_tikz_contents(y_pos, user_spec, default_rows, columns, row_height):
    position = "{:f} cm".format(y_pos)
    first_line = user_spec["first_name"]
    if "supervisor" in user_spec:
        second_line = "({:s})".format(user_spec["supervisor"])
    else:
        second_line = user_spec["last_name"]

    if "rows" in user_spec:
        rows = user_spec["rows"]
    else:
        rows = default_rows

    row_count = str(rows)
    ticks = str(2 * rows)
    size = str(rows * columns)
    y_min = str(- rows * 0.5 * row_height)

    return "/".join((position, first_line, second_line, row_count, ticks, size, y_min))


def create_tally_sheets(filename):
    with codecs.open(filename, "r", encoding="utf-8") as f:
        data = yaml.load(f)

    single_sheets = (
        make_single_sheet(group, users, data)
        for group, users in data["groups"].items()
        )

    tex_filename = Template(data["filename_template"]).substitute(
        datestamp=date.today().isoformat(),
        )

    with codecs.open(tex_filename, "w", encoding="utf-8") as f:
        f.write(make_main_file(single_sheets, data))

    for i in range(data["num_pdflatex_runs"]):
        print("Running pdflatex ({:d}/{:d})...".format(
            i + 1,
            data["num_pdflatex_runs"],
            ))
        run_pdflatex(".", tex_filename)

    clean_temp_files()


def clean_temp_files():
    temp_file_extensions = [
        r"\.aux",
        r"\.out",
        r"\.log",
        r"\.synctex\.gz",
        r"\.preview\.pdf",
        ]
    temp_files_pattern = "({:s})$".format("|".join(temp_file_extensions))
    for f in os.listdir("."):
        if re.search(temp_files_pattern, f):
            os.remove(os.path.join(".", f))


if __name__ == "__main__":
    create_tally_sheets(sys.argv[1])
