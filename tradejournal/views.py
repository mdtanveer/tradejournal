"""
Routes and views for the flask application.
"""
import json
from datetime import datetime

from flask import render_template, redirect, request, Response
from wtforms import Form, validators, StringField, SubmitField, FloatField, DateTimeField, IntegerField, TextAreaField, BooleanField

from tradejournal.models import JournalEntry, JournalEntryNotFound, toIST_fromtimestamp, IST_now, yahooquotes
from tradejournal.models.factory import create_repository
from tradejournal.settings import REPOSITORY_NAME, REPOSITORY_SETTINGS
from flask_login import login_required
from flask_paginate import Pagination, get_page_parameter, get_page_args
import jsonpickle
from flask import current_app as app
import sys, traceback

repository = create_repository(REPOSITORY_NAME, REPOSITORY_SETTINGS)

class CommentForm(Form):
    title = StringField('Title:')
    text = TextAreaField('Text', validators=[validators.required()])
    linkchart = BooleanField()

class ChartForm(Form):
    title = StringField('Title:')

@app.route('/')
@app.route('/home')
@login_required
def home():
    """Renders the home page, with a list of all journalentrys."""
    journalentries=repository.get_journalentries()
    page, per_page, offset = get_page_args()
    pagination = Pagination(page=page, total=len(journalentries), search=False, record_name='journalentries',css_framework='bootstrap4')
    return render_template(
        'index.html',
        title='Journal Entries',
        year=datetime.now().year,
        journalentries=journalentries[offset:offset+per_page],
        pagination=pagination
    )

@app.route('/js/<path:path>')
@login_required
def send_js(path):
    return send_from_directory('js', path)

@app.route('/contact')
@login_required
def contact():
    """Renders the contact page."""
    return render_template(
        'contact.html',
        title='Contact',
        year=datetime.now().year,
    )

@login_required
@app.route('/about')
def about():
    """Renders the about page."""
    return render_template(
        'about.html',
        title='About',
        year=datetime.now().year,
        repository_name=repository.name,
    )

@app.route('/seed', methods=['POST', 'GET'])
@login_required
def seed():
    """Seeds the database with sample journalentrys."""
    repository.add_sample_journalentries()
    return redirect('/')

@app.route('/results/<key>')
@login_required
def results(key):
    """Renders the results page."""
    journalentry = repository.get_journalentry(key)
    journalentry.calculate_stats()
    return render_template(
        'results.html',
        title='Results',
        year=datetime.now().year,
        journalentry=journalentry,
    )

@app.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """New journal entry"""
    if request.method == 'POST':
        if request.get_json():
            data = request.get_json()
        else:
            data = request.form
        repository.create_journalentries(data)
        return redirect('/')
    else:
        journalentry = JournalEntry(None, {})
        journalentry.entry_time = IST_now()
        return render_template(
        'create.html',
        journalentry = journalentry,
        zero_exit = True,
        pagetitle = "Create New",
        subtitle = "Create New Journal Entry"
    )


@app.route('/journalentry/<key>/edit', methods=['GET', 'POST'])
@login_required
def edit(key):
    """New journal entry"""
    if request.method == 'POST':
        if request.get_json():
            data = request.get_json()
        else:
            data = request.form
        repository.update_journalentry(key, data)
        return redirect('/journalentry/{0}/edit'.format(key))
    else:
        journalentry=repository.get_journalentry(key)

        return render_template(
            'create.html',
            journalentry = journalentry,
            zero_exit = (journalentry.exit_time == toIST_fromtimestamp(0)),
            pagetitle = "Edit Entry",
            subtitle = "Edit Journal Entry"
        )

@app.route('/journalentry/<key>/delete', methods=['GET'])
@login_required
def delete_entry(key):
    """Deletes the journalentry page."""
    repository.delete_journalentry(key)
    return redirect('/')

@app.route('/journalentry/<key>/comments', methods=['GET', 'POST'])
@login_required
def comments(key):
    """Renders the comments page."""
    error_message = ''
    if request.method == 'POST':
        try:
            if request.get_json():
                data = request.get_json()
            else:
                data = request.form
            linkchart = dict(data).pop('linkchart', False)
            repository.add_comment(key, data)
            if linkchart:
                repository.add_chart(key, {'title':data['title']})
            return redirect('/journalentry/{0}/comments'.format(key))
        except KeyError:
            error_message = 'Unable to update'
    else:
        form = CommentForm()
        comments=repository.get_comments(key)
        page, per_page, offset = get_page_args()
        pagination = Pagination(page=page, total=len(comments), search=False, record_name='comments',css_framework='bootstrap4')
        return render_template(
            'comments.html',
            error_message=error_message,
            form = form,
            comments=comments[offset:offset+per_page],
            journalentry=repository.get_journalentry(key),
            allcomments = False,
            pagination = pagination
        )

@app.route('/journalentry/comments', methods=['GET', 'POST'])
@login_required
def allcomments():
    """Renders the all comments page."""
    error_message = ''
    if request.method == 'POST':
        try:
            if request.get_json():
                data = request.get_json()
            else:
                data = request.form
            repository.add_comment("GLOBAL_1", data)
            return redirect('/journalentry/comments')
        except KeyError:
            error_message = 'Unable to update'
    else:
        form = CommentForm()
        page, per_page, offset = get_page_args()
        comments=repository.get_all_comments()
        pagination = Pagination(page=page, total=len(comments), search=False, record_name='comments',css_framework='bootstrap4')
        return render_template(
            'comments.html',
            comments=comments[offset:offset+per_page],
            error_message=error_message,
            form = form,
            allcomments=True,
            pagination = pagination
        )

@app.route('/journalentry/<key>/charts', methods=['GET', 'POST'])
@login_required
def charts(key):
    """Renders the charts page."""
    error_message = ''
    journalentry = repository.get_journalentry(key)

    if request.method == 'POST':
        try:
            if request.get_json():
                data = request.get_json()
            else:
                data = request.form
            repository.add_chart(key, data, journalentry.get_timeframe())
            return redirect('/journalentry/{0}/charts'.format(key))
        except KeyError:
            error_message = 'Unable to update'
    else:
        form = ChartForm()
        return render_template(
            'chart.html',
            charts=jsonpickle.encode(repository.get_charts(key), unpicklable=False),
            error_message=error_message,
            form = form,
            journalentry=repository.get_journalentry(key),
            timeframe=journalentry.get_timeframe(),
            indicator=journalentry.get_indicator(),
            trades = repository.get_trades(key),
        )

@app.route('/journalentry/<key>/charts/<chartid>', methods=['GET'])
@login_required
def chart_data(key, chartid):
    csv_data = repository.get_chart_data(chartid)
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-disposition":
                    "attachment; filename=%s"%chartid})

@app.route('/charts', methods=['GET'])
def quick_charts():
    """Renders the charts page."""
    error_message = ''
    if 'symbols' in request.args.keys():
        symbols = request.args['symbols'].split(',')
        tf = request.args.get('tf', '2h')
        indicator = request.args.get('ind', 'stochastic')
        charts = [{'key':'', 'title': symbol, 'data': symbol, 'relativeUrl':'charts/%s?tf=%s'%(symbol, tf)} for symbol in symbols]
        return render_template(
            'chart.html',
            charts=jsonpickle.encode(charts, unpicklable=False),
            error_message=error_message,
            journalentry=None,
            timeframe=tf,
            indicator=indicator,
        )
    else:
        return ('', 204)

@app.route('/charts/<symbol>', methods=['GET'])
def fetch_chart(symbol):
    tf = request.args.get('tf', '2h')
    if tf == '2h' or tf == '1h':
        yahoo_params = (symbol, '90d', '1h', '.BO')
    elif tf == '1d':
        yahoo_params = (symbol, '1y', '1d', '.NS')
    elif tf == '1wk':
        yahoo_params = (symbol, '5y', '1wk', '.NS')
    else:
        raise Exception('Unrecognized timeframe')
    csv_data=yahooquotes.get_quote_data(*yahoo_params).to_csv(index=False)
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-disposition":
                    "attachment; filename=%s.csv"%symbol})


@app.route('/journalentry/<key>/trades', methods=['GET'])
@login_required
def trades(key):
    """Renders the trades page."""
    journalentry = repository.get_journalentry(key)
    return render_template(
        'trades.html',
        journalentry=journalentry,
        trades = repository.get_trades(key),
    )

@app.route('/journalentry/trades', methods=['GET'])
@login_required
def all_trades():
    """Renders the trades page."""
    return render_template(
        'trades.html',
        journalentry=None,
        trades = repository.get_all_trades(),
    )

@app.route('/positions', methods=['GET'])
@login_required
def positions():
    groupby = request.args.get('groupby', 'strategy')
    """Renders the positions page."""
    error = None
    try:
        position_data = repository.get_position_data(groupby)
    except Exception:
        exc_type, exc_value, exc_tb = sys.exc_info()
        error = traceback.format_exception(exc_type, exc_value, exc_tb)
    if position_data:
        position_data.sort(key=lambda x: x[0]['name'], reverse=True)
        return render_template(
            'positions.html',
            data = position_data,
            error=error,
        )

@app.route('/journalentry/<key>/charts/<chartkey>/delete', methods=['DELETE'])
@login_required
def chart_delete(key, chartkey):
    repository.delete_chart(chartkey)
    return Response("{}", status=200, mimetype='application/json')

@app.errorhandler(JournalEntryNotFound)
def page_not_found(error):
    """Renders error page."""
    return 'JournalEntry does not exist.', 404

@app.template_filter('formatdatetimeinput')
def format_datetime(value, format="%Y-%m-%dT%H:%M"):
    if value is None:
        return ""
    return value.strftime(format)


@app.template_filter('formatdatetimedisplay')
def format_datetime(value, format="%d-%m-%Y %I:%M %p"):
    if value is None:
        return ""
    now = IST_now()
    if now.year == value.year:
        return value.strftime("%h %d, %I:%M %p")
    else:
        return value.strftime(format)

@app.template_filter('formatdatetimed3')
def format_datetime(value, format="%Y-%m-%d %H:%M:%S"):
    if value is None:
        return ""
    return value.strftime(format)
