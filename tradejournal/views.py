"""
Routes and views for the flask application.
"""

from datetime import datetime

from flask import render_template, redirect, request

from tradejournal import app
from tradejournal.models import JournalEntryNotFound
from tradejournal.models.factory import create_repository
from tradejournal.settings import REPOSITORY_NAME, REPOSITORY_SETTINGS

repository = create_repository(REPOSITORY_NAME, REPOSITORY_SETTINGS)

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

@app.route('/create', methods=['POST'])
def create():
    """New journal entry"""
    repository.create_journalentries(request.get_json())
    return redirect('/')

@app.route('/journalentry/<key>', methods=['GET', 'POST'])
def details(key):
    """Renders the journalentry details page."""
    error_message = ''
    if request.method == 'POST':
        try:
            choice_key = request.form['choice']
            repository.increment_vote(key, choice_key)
            return redirect('/results/{0}'.format(key))
        except KeyError:
            error_message = 'Please make a selection.'

    return render_template(
        'details.html',
        journalentry=repository.get_journalentry(key),
        error_message=error_message,
    )

@app.errorhandler(JournalEntryNotFound)
def page_not_found(error):
    """Renders error page."""
    return 'JournalEntry does not exist.', 404
