#!/usr/bin/env python

#-----------------------------------------------------------------------
# runserver.py
# Author: Ranajoy Gupta
#-----------------------------------------------------------------------

"""Flask web server for the Registrar application."""

import sys
import argparse
import sqlite3
import contextlib
import json
import flask

app = flask.Flask(__name__, template_folder='.')

DATABASE_URL = 'file:reg.sqlite?mode=ro'
GENERIC_ERROR_MSG = (
    "A server error occurred. "
    "Please contact the system administrator."
)

def escape_wildcards(user_input):
    """Escapes SQLite wildcards for LIKE clauses."""
    escaped = user_input.replace('\\', '\\\\')
    escaped = escaped.replace('%', '\\%')
    escaped = escaped.replace('_', '\\_')
    return f"%{escaped}%"

def get_overviews(criteria):
    """Queries database for class overviews."""
    dept = escape_wildcards(criteria.get('dept', ''))
    coursenum = escape_wildcards(criteria.get('coursenum', ''))
    area = escape_wildcards(criteria.get('area', ''))
    title = escape_wildcards(criteria.get('title', ''))

    stmt = """
        SELECT classid, dept, coursenum, area, title
        FROM courses, crosslistings, classes
        WHERE (courses.courseid = crosslistings.courseid)
        AND (courses.courseid = classes.courseid)
        AND (dept LIKE ? ESCAPE '\\')
        AND (coursenum LIKE ? ESCAPE '\\')
        AND (area LIKE ? ESCAPE '\\')
        AND (title LIKE ? ESCAPE '\\')
        ORDER BY dept, coursenum, classid
    """

    with contextlib.closing(sqlite3.connect(
            DATABASE_URL, isolation_level=None, uri=True
    )) as connection:
        with contextlib.closing(connection.cursor()) as cursor:
            cursor.execute(stmt, [dept, coursenum, area, title])
            rows = cursor.fetchall()

            payload = []
            for row in rows:
                payload.append({
                    'classid': row[0],
                    'dept': row[1] or "",
                    'coursenum': row[2] or "",
                    'area': row[3] or "",
                    'title': row[4] or ""
                })
            return payload

def get_class_row(cursor, classid):
    """Retrieves class details."""
    cursor.execute('''
        SELECT courseid, days, starttime, endtime, bldg, roomnum
        FROM classes WHERE classid = ?
    ''', [classid])
    return cursor.fetchone()

def get_deptcoursenums(cursor, courseid):
    """Retrieves crosslistings for a course."""
    cursor.execute('''
        SELECT dept, coursenum FROM crosslistings
        WHERE courseid = ? ORDER BY dept, coursenum
    ''', [courseid])
    return [f"{row[0]} {row[1]}" for row in cursor.fetchall()]

def get_course_row(cursor, courseid):
    """Retrieves course details."""
    cursor.execute('''
        SELECT area, title, descrip, prereqs
        FROM courses WHERE courseid = ?
    ''', [courseid])
    return cursor.fetchone()

def get_profnames(cursor, courseid):
    """Retrieves professor names for a course."""
    cursor.execute('''
        SELECT profname FROM coursesprofs, profs
        WHERE coursesprofs.profid = profs.profid
        AND coursesprofs.courseid = ? ORDER BY profname
    ''', [courseid])
    return [row[0] for row in cursor.fetchall()]

def get_details(classid):
    """Queries database for specific class details."""
    with contextlib.closing(sqlite3.connect(
            DATABASE_URL, isolation_level=None, uri=True
    )) as connection:
        with contextlib.closing(connection.cursor()) as cursor:
            class_row = get_class_row(cursor, classid)
            if class_row is None:
                return None

            courseid = class_row[0]
            deptcoursenums = get_deptcoursenums(cursor, courseid)
            course_row = get_course_row(cursor, courseid)
            profnames = get_profnames(cursor, courseid)

            payload = {
                'classid': classid,
                'courseid': courseid,
                'days': class_row[1] or "",
                'starttime': class_row[2] or "",
                'endtime': class_row[3] or "",
                'bldg': class_row[4] or "",
                'roomnum': class_row[5] or "",
                'deptcoursenums': deptcoursenums,
                'area': course_row[0] or "",
                'title': course_row[1] or "",
                'descrip': course_row[2] or "",
                'prereqs': course_row[3] or "",
                'profnames': profnames
            }
            return payload

@app.route('/', methods=['GET'])
@app.route('/index', methods=['GET'])
def index():
    """Route for the main SPA page."""
    try:
        return flask.send_file('index.html')
    except Exception as ex:
        print(f"{sys.argv[0]}: {ex}", file=sys.stderr)
        json_doc = json.dumps([False, GENERIC_ERROR_MSG])
        response = flask.make_response(json_doc)
        response.headers['Content-Type'] = 'application/json'
        return response

@app.route('/regoverviews', methods=['GET'])
def overviews():
    """API endpoint for class overviews search."""
    try:
        dept = flask.request.args.get('dept', '')
        coursenum = flask.request.args.get('coursenum', '')
        area = flask.request.args.get('area', '')
        title = flask.request.args.get('title', '')

        criteria = {
            'dept': dept,
            'coursenum': coursenum,
            'area': area,
            'title': title
        }

        classes = get_overviews(criteria)
        json_doc = json.dumps([True, classes])
        response = flask.make_response(json_doc)
        response.headers['Content-Type'] = 'application/json'
        return response

    except Exception as ex:
        print(f"{sys.argv[0]}: {ex}", file=sys.stderr)
        json_doc = json.dumps([False, GENERIC_ERROR_MSG])
        response = flask.make_response(json_doc)
        response.headers['Content-Type'] = 'application/json'
        return response

@app.route('/regdetails', methods=['GET'])
def details():
    """API endpoint for class details."""
    try:
        classid_str = flask.request.args.get('classid')

        if classid_str is None or classid_str.strip() == '':
            json_doc = json.dumps([False, "missing classid"])
            response = flask.make_response(json_doc)
            response.headers['Content-Type'] = 'application/json'
            return response

        try:
            classid = int(classid_str)
        except ValueError:
            json_doc = json.dumps([False, "non-integer classid"])
            response = flask.make_response(json_doc)
            response.headers['Content-Type'] = 'application/json'
            return response

        class_details = get_details(classid)

        if class_details is None:
            json_doc = json.dumps([False, f"no class with classid {classid} exists"])
            response = flask.make_response(json_doc)
            response.headers['Content-Type'] = 'application/json'
            return response

        json_doc = json.dumps([True, class_details])
        response = flask.make_response(json_doc)
        response.headers['Content-Type'] = 'application/json'
        return response

    except Exception as ex:
        print(f"{sys.argv[0]}: {ex}", file=sys.stderr)
        json_doc = json.dumps([False, GENERIC_ERROR_MSG])
        response = flask.make_response(json_doc)
        response.headers['Content-Type'] = 'application/json'
        return response

def main():
    """Parses command-line arguments and runs the Flask server."""
    parser = argparse.ArgumentParser(
        description="The registrar application"
    )
    parser.add_argument('port', metavar='port', type=int,
                        help='the port at which the server '
                             'should listen')

    args = parser.parse_args()

    try:
        app.run(host='0.0.0.0', port=args.port, debug=False)
    except Exception as ex:
        print(f"{sys.argv[0]}: {ex}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
