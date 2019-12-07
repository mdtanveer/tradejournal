"""
Routes and views for the flask application.
"""
import json
from datetime import datetime

from flask import render_template, redirect, request, Response
from wtforms import Form, validators, StringField, SubmitField, FloatField, DateTimeField, IntegerField, TextAreaField

from tradejournal import app
from tradejournal.models import JournalEntryNotFound, toIST_fromtimestamp, IST_now
from tradejournal.models.factory import create_repository
from tradejournal.settings import REPOSITORY_NAME, REPOSITORY_SETTINGS

repository = create_repository(REPOSITORY_NAME, REPOSITORY_SETTINGS)

class CommonJournalEntryForm(Form):
    exit_time = DateTimeField('Exit Time:')
    entry_price = FloatField('Entry Price:')
    exit_price = FloatField('Exit Price:')
    quantity = IntegerField('Quantity:', validators=[validators.required()])
    entry_sl = FloatField('Entry SL:')
    entry_target = FloatField('Entry Target:')
    direction = StringField('Direction:', validators=[validators.required()])

class EditJournalEntryForm(Form):
    rating = StringField('Rating:')

class NewJournalEntryForm(CommonJournalEntryForm):
    symbol = StringField('Symbol:', validators=[validators.required()])
    entry_time = DateTimeField('Entry Time:', validators=[validators.required()])

class CommentForm(Form):
    title = StringField('Title:')
    text = TextAreaField('Text', validators=[validators.required()])

class ChartForm(Form):
    title = StringField('Title:')

@app.route('/')
@app.route('/home')
def home():
    """Renders the home page, with a list of all journalentrys."""
    return render_template(
        'index.html',
        title='Journal Entries',
        year=datetime.now().year,
        journalentries=repository.get_journalentries()
    )

@app.route('/js/<path:path>')
def send_js(path):
    return send_from_directory('js', path)

@app.route('/contact')
def contact():
    """Renders the contact page."""
    return render_template(
        'contact.html',
        title='Contact',
        year=datetime.now().year,
    )

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
def seed():
    """Seeds the database with sample journalentrys."""
    repository.add_sample_journalentries()
    return redirect('/')

@app.route('/results/<key>')
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
def create():
    """New journal entry"""
    form = NewJournalEntryForm()
    if request.method == 'POST':
        if request.get_json():
            data = request.get_json()
        else:
            data = request.form
        repository.create_journalentries(data)
        return redirect('/')
    else:
        return render_template(
        'create.html',
        form=form,
        nowTime = IST_now()
    )


@app.route('/journalentry/<key>/edit', methods=['GET', 'POST'])
def edit(key):
    """New journal entry"""
    if request.method == 'POST':
        if request.get_json():
            data = request.get_json()
        else:
            data = request.form
        repository.update_journalentry(key, data)
        return redirect('/journalentry/{0}'.format(key))
    else:
        form = EditJournalEntryForm()
        journalentry=repository.get_journalentry(key)

        return render_template(
            'edit.html',
            form = form,
            journalentry = journalentry,
            zero_exit = (journalentry.exit_time == toIST_fromtimestamp(0))
        )

@app.route('/journalentry/<key>', methods=['GET', 'POST'])
def details(key):
    """Renders the journalentry details page."""
    error_message = ''
    return render_template(
        'details.html',
        journalentry=repository.get_journalentry(key),
        error_message=error_message,
    )

@app.route('/journalentry/<key>/comments', methods=['GET', 'POST'])
def comments(key):
    """Renders the comments page."""
    error_message = ''
    if request.method == 'POST':
        try:
            if request.get_json():
                data = request.get_json()
            else:
                data = request.form
            repository.add_comment(key, data)
            return redirect('/journalentry/{0}/comments'.format(key))
        except KeyError:
            error_message = 'Unable to update'
    else:
        form = CommentForm()
        return render_template(
            'comments.html',
            comments=repository.get_comments(key),
            error_message=error_message,
            form = form,
            journalentry=repository.get_journalentry(key),
            allcomments = False
        )

@app.route('/journalentry/comments', methods=['GET', 'POST'])
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
        return render_template(
            'comments.html',
            comments=repository.get_all_comments(),
            error_message=error_message,
            form = form,
            allcomments=True
        )

@app.route('/journalentry/<key>/charts', methods=['GET', 'POST'])
def charts(key):
    """Renders the charts page."""
    error_message = ''
    if request.method == 'POST':
        try:
            if request.get_json():
                data = request.get_json()
            else:
                data = request.form
            repository.add_chart(key, data)
            return redirect('/journalentry/{0}/charts'.format(key))
        except KeyError:
            error_message = 'Unable to update'
    else:
        form = ChartForm()
        return render_template(
            'chart.html',
            charts=repository.get_charts(key),
            base_url = request.url,
            error_message=error_message,
            form = form,
            symbol = key.split('_')[0]
        )

@app.route('/journalentry/<key>/charts/<chartid>', methods=['GET'])
def chart_data(key, chartid):
    csv_data = repository.get_chart_data(chartid)
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-disposition":
                 "attachment; filename=%s"%chartid})

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