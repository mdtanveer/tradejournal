"""
Routes and views for the flask application.
"""
import json
from datetime import datetime

from flask import render_template, make_response, redirect, request, Response, session, url_for

from tradejournal.models import JournalEntry, JournalEntryGroup, JournalEntryNotFound, toIST_fromtimestamp, IST_now, yahooquotes, resample
from tradejournal.models.factory import create_repository
from tradejournal.settings import REPOSITORY_NAME, REPOSITORY_SETTINGS
from flask_login import login_required
from flask_paginate import Pagination, get_per_page_parameter, get_page_args
import jsonpickle
from flask import current_app as app
import sys, traceback
import plotly
import plotly.express as px


repository = create_repository(REPOSITORY_NAME, REPOSITORY_SETTINGS)

@app.route('/')
@app.route('/home')
@login_required
def home():
    """Renders the home page, with a list of all journalentrys."""
    journalentries=repository.get_journalentries_forview()
    journalentrygroups=repository.get_journalentrygroups_forview(journalentries)
    journalentries.extend(journalentrygroups)
    journalentries.sort(key = lambda x: (x.is_open(), x.entry_time), reverse=True)

    categories = {}
    for je in journalentries:
        for category in je.get_category():
            if category not in categories.keys():
                categories[category] = []
            categories[category].append(je)
    
    page, per_page, offset = get_page_args()
    try:
        subpage = request.args['subpage']
    except:
        subpage = request.cookies.get('subpage', 'open')

    entries = []
    if subpage != request.cookies.get('subpage', 'open'):
        page = int(request.cookies.get('page_'+subpage, "1"))
        offset = per_page*(page-1)

    if subpage == 'open':
        entries = list(filter(lambda x: x.is_open() and not x.isidea(), journalentries))
    elif subpage == 'closed':
        entries = list(filter(lambda x: not x.is_open() and not x.isidea(), journalentries))
    elif subpage in categories.keys():
        entries = categories[subpage]
    elif subpage == 'all':
        entries = journalentries

    pagination = Pagination(page=page, per_page=per_page, total=len(entries), search=False, record_name='journalentries',css_framework='bootstrap4')
    response = make_response(render_template(
        'index.html',
        title='Journal Entries',
        year=datetime.now().year,
        journalentries=entries[offset:offset+per_page],
        pagination=pagination,
        subpage=subpage,
        categories = categories.keys()
    ))
    response.set_cookie('subpage', subpage)
    response.set_cookie('page_'+subpage, str(page))
    return response

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
        if request.get_json(silent=True):
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
        pagetitle = "Create New",
        subtitle = "Create New Journal Entry"
    )

@app.route('/creategroup', methods=['GET', 'POST'])
@login_required
def creategroup():
    """New journal entry"""
    if request.method == 'POST':
        if request.get_json(silent=True):
            data = request.get_json()
        else:
            data = request.form
        repository.create_journalentrygroup(data)
        return redirect('/')
    else:
        members_param = request.args.get('createwith')  # Get the value of the 'members' parameter from the URL
        journalentrygroup = JournalEntryGroup(None, {})
        journalentrygroup.entry_time = IST_now()
        return render_template(
        'creategroup.html',
        journalentrygroup = journalentrygroup,
        pagetitle = "Create New",
        subtitle = "Create New Journal Entry Group",
        members = members_param
    )

def lastget_url(default):
    try:
        return session['lastget']
    except:
        return default

@app.route('/journalentry/<key>/edit', methods=['GET', 'POST'])
@login_required
def edit(key):
    """New journal entry"""
    if request.method == 'POST':
        if request.get_json(silent=True):
            data = request.get_json()
        else:
            data = request.form
        repository.update_journalentry(key, data)
        return redirect(lastget_url('/journalentry/{0}/charts'.format(key)))
    else:
        journalentry=repository.get_journalentry(key)
        session['lastget'] = request.referrer

        return render_template(
            'create.html',
            journalentry = journalentry,
            pagetitle = "Edit Entry",
            subtitle = "Edit Journal Entry"
        )

@app.route('/journalentry/<key>/duplicate', methods=['GET', 'POST'])
@login_required
def duplicate(key):
    """Duplicate journal entry"""
    if request.method == 'POST':
        if request.get_json(silent=True):
            data = request.get_json()
        else:
            data = request.form
        repository.create_journalentries(data)
        return redirect('/')
    journalentry=repository.get_journalentry(key)
    journalentry.entry_time = IST_now()

    return render_template(
        'create.html',
        journalentry = journalentry,
        pagetitle = "Duplicate Entry",
        subtitle = "Duplicate Journal Entry"
    )

@app.route('/journalentrygroup/<key>/edit', methods=['GET', 'POST'])
@login_required
def editgroup(key):
    """New journal entry"""
    if request.method == 'POST':
        if request.get_json(silent=True):
            data = request.get_json()
        else:
            data = request.form
        repository.update_journalentrygroup(key, data)
        return redirect(lastget_url('/journalentrygroup/{0}/view'.format(key)))
    else:
        journalentrygroup=repository.get_journalentrygroup(key)
        session['lastget'] = request.referrer

        return render_template(
            'creategroup.html',
            journalentrygroup = journalentrygroup,
            pagetitle = "Edit Group Entry",
            subtitle = "Edit Journal Entry Group"
        )

@app.route('/journalentrygroup/<key>/copyattributestochildren', methods=['POST'])
@login_required
def copyattributestochildren(key):
    if request.method == 'POST':
        journalentrygroup=repository.get_journalentrygroup(key)
        repository.copyattributestochildren(journalentrygroup)
        return redirect(lastget_url('/journalentrygroup/{0}/view'.format(key)))

@app.route('/journalentrygroup/<key>/view', methods=['GET'])
@login_required
async def viewgroup(key):
    groupby = request.args.get('groupby', 'none')
    force_refresh = int(request.args.get('nocache', 0))
    journalentrygroup=repository.get_journalentrygroup(key)
    await journalentrygroup.fetch_exit_price_as_ltp(force_refresh)
    comments=repository.get_comments(key)
    page, per_page, offset = get_page_args()
    pagination = Pagination(page=page, total=len(comments), search=False, record_name='comments',css_framework='bootstrap4')

    return render_template(
        'groupview.html',
        journalentrygroup = journalentrygroup.groupby(groupby),
        pagetitle = "Group Entry",
        subtitle = "View Journal Entry Group",
        comments = comments,
        pagination = pagination,
    )

@app.route('/journalentrygroup/<key>/analysis', methods=['GET'])
@login_required
async def viewgroupanalysis(key):
    journalentrygroup=repository.get_journalentrygroup(key)
    profit_ranges = ""
    extrema_profits = ""
    optionlab_result = None
    graph = None
    try:
        optionlab_result = await journalentrygroup.get_optionlab_result_async()
        size = len(optionlab_result.data.stock_price_array)
        k = int(size/500)
        fig = px.line(x=optionlab_result.data.stock_price_array[:-k:k], y=optionlab_result.data.strategy_profit[:-k:k])
        graph = fig.to_html(full_html = False, include_plotlyjs ='cdn')
        for low, high in optionlab_result.profit_ranges:
            profit_ranges += "%.1f-%.1f " % (low, high)
        extrema_profits = "%.2f / %.2f"%(optionlab_result.data.strategy_profit[0], optionlab_result.data.strategy_profit[-1]) 
        print(profit_ranges)
        print(extrema_profits)
    except Exception as err:
        print("Unable to do optionlab analysis:", err)

    return render_template(
        'groupanalysis.html',
        journalentrygroup = journalentrygroup,
        pagetitle = "Group Analysis",
        subtitle = "View Journal Entry Group Analysis",
        optionlab_result = optionlab_result,
        graph = graph,
        profit_ranges = profit_ranges,
        extrema_profits = extrema_profits
    )

@app.route('/journalentrygroup/<key>/delete', methods=['GET'])
@login_required
def delete_entrygroup(key):
    """Deletes the journalentrygroup page."""
    repository.delete_journalentrygroup(key)
    return redirect('/')

@app.route('/journalentrygroup/<key>/comments', methods=['GET', 'POST'])
@login_required
def commentsgroup(key):
    """Renders the comments page."""
    error_message = ''
    if request.method == 'POST':
        try:
            if request.get_json(silent=True):
                data = request.get_json()
            else:
                data = request.form
            linkchart = dict(data).pop('linkchart', False)
            repository.add_comment(key, data)
            if linkchart:
                repository.add_chart(key, {'title':data['title']})
            return redirect('/journalentrygroup/{0}/view'.format(key))
        except KeyError:
            error_message = 'Unable to add comment'
    else:
        comments=repository.get_comments(key)
        page, per_page, offset = get_page_args()
        pagination = Pagination(page=page, total=len(comments), search=False, record_name='comments',css_framework='bootstrap4')
        return render_template(
            'comments.html',
            error_message=error_message,
            comments=comments[offset:offset+per_page],
            journalentrygroup=repository.get_journalentrygroup(key),
            allcomments = False,
            pagination = pagination
        )

@app.route('/journalentry/<key>/comments/<commentid>', methods=['POST', 'DELETE'])
@login_required
def update_or_delete_comment(key, commentid):
    """Renders the comments page."""
    error_message = ''
    if request.method == 'POST':
        try:
            if request.get_json(silent=True):
                data = request.get_json()
            else:
                data = request.form
            repository.update_comment(commentid, data)
            return redirect('/journalentry/{0}'.format(key))
        except KeyError:
            error_message = 'Unable to update comment'
    elif request.method == "DELETE":
        try:
            repository.delete_comment(commentid)
            return redirect('/journalentry/{0}'.format(key))
        except KeyError:
            error_message = 'Unable to delete comment'

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
            if request.get_json(silent=True):
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
        comments=repository.get_comments(key)
        page, per_page, offset = get_page_args()
        pagination = Pagination(page=page, total=len(comments), search=False, record_name='comments',css_framework='bootstrap4')
        return render_template(
            'comments.html',
            error_message=error_message,
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
            if request.get_json(silent=True):
                data = request.get_json()
            else:
                data = request.form
            repository.add_comment("GLOBAL_1", data)
            return redirect('/journalentry/comments')
        except KeyError:
            error_message = 'Unable to update'
    else:
        page, per_page, offset = get_page_args()
        comments=repository.get_all_comments()
        pagination = Pagination(page=page, total=len(comments), search=False, record_name='comments',css_framework='bootstrap4')
        return render_template(
            'comments.html',
            comments=comments[offset:offset+per_page],
            error_message=error_message,
            allcomments=True,
            pagination = pagination
        )

def chartview_helper(journalentry, indicator, overlay_indicator, error_message):
    key = journalentry.key
    comments=repository.get_comments(key)
    page, per_page, offset = get_page_args()
    pagination = Pagination(page=page, total=len(comments), search=False, record_name='comments',css_framework='bootstrap4')
    return render_template(
        'chart.html',
        charts=jsonpickle.encode(repository.get_charts(key), unpicklable=False),
        error_message=error_message,
        journalentry=journalentry,
        timeframe=journalentry.get_timeframe(),
        indicator=indicator,
        overlay_indicator=overlay_indicator,
        trades = repository.get_trades(key),
        comments=comments[offset:offset+per_page],
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
            if request.get_json(silent=True):
                data = request.get_json()
            else:
                data = request.form
            repository.add_chart(key, data, journalentry.get_timeframe())
        except KeyError:
            error_message = 'Unable to update'
    indicator = request.args.get('ind', journalentry.get_indicator())
    overlay_indicator = request.args.get('oind', 'ichimoku')
    return chartview_helper(journalentry, indicator, overlay_indicator, error_message)

@app.route('/journalentry/<key>/charts/<chartid>', methods=['GET'])
@login_required
def chart_data(key, chartid):
    tf = request.args.get('tf', '2h')
    typ = request.args.get('type', 'original')
    csv_data = repository.get_chart_data(chartid, tf, typ)
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
        overlay_indicator = request.args.get('oind', 'ichimoku')

        charts = [{'key':'', 'title': symbol, 'data': symbol, 'relativeUrl':'charts/%s?tf=%s'%(symbol, tf)} for symbol in symbols]
        return render_template(
            'publicchart.html',
            charts=jsonpickle.encode(charts, unpicklable=False),
            error_message=error_message,
            journalentry=None,
            timeframe=tf,
            indicator=indicator,
            overlay_indicator=overlay_indicator,
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
    yd=yahooquotes.get_quote_data(*yahoo_params)
    
    # For intraday, always override to 2h timeframe
    if tf == '2h' or tf == '1h':
        yd = resample.resample_quote_data(yd, '2H')
    
    csv_data = yd.to_csv(index=False)
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


@app.route('/positions', methods=['GET', 'POST'])
@login_required
def positions():
    groupby = request.args.get('groupby', 'strategy')
    """Renders the positions page."""
    error = None
    position_data = None
    grand_total = 0
    try:
        repository.try_login_zerodha()
    except Exception:
        return redirect('/zerodha1')
    
    position_data, grand_total = repository.get_position_data(groupby)
    if position_data:
        position_data.sort(key=lambda x: x[0]['name'], reverse=True)

    return render_template(
        'positions.html',
        data = position_data,
        error=None,
        grand_total = grand_total
    )

@app.route('/zerodha1', methods=['GET', 'POST'])
@login_required
def zerodha1():
    if request.method == "POST":
        session["zerodha_step1"] = repository.login_zerodha_step1(request.form["username"], request.form["password"])
        return redirect("/zerodha2")
    return render_template('zerodha1.html', error=None)

@app.route('/zerodha2', methods=['GET', 'POST'])
@login_required
def zerodha2():
    if request.method == "POST":
        session["zerodha_step2"] = repository.login_zerodha_step2(request.form["twofa"], session["zerodha_step1"])
        return redirect("/positions")
    return render_template('zerodha2.html', error=None)

@app.route('/journalentry/monthlyreview/<year>/<month>/<serial>', methods=['GET'])
@login_required
def monthly_review(year, month, serial):
    """Renders the monthly review page."""
    journalentry = repository.get_journalentry_for_monthly_review(int(year), int(month), int(serial))

    indicator = request.args.get('ind', journalentry.get_indicator())
    overlay_indicator = request.args.get('oind', 'ichimoku')
    return chartview_helper(journalentry, indicator, overlay_indicator, '')


@app.route('/journalentry/<key>/charts/<chartkey>/delete', methods=['DELETE'])
@login_required
def chart_delete(key, chartkey):
    repository.delete_chart(chartkey)
    return Response("{}", status=200, mimetype='application/json')

@app.route('/tradesignals/<date>/<timeframe>/<strategy>', methods=['GET'])
def tradesignals(date, timeframe, strategy):
    """Renders the charts page."""
    error_message = ''
    tf = request.args.get('tf', '2h')
    indicator = request.args.get('ind', 'stochastic')
    overlay_indicator = request.args.get('oind', 'ichimoku')
    tradesignals = repository.get_tradesignals(date, timeframe, strategy)
    charts = [{'key':'', 
                'title': t.symbol,
                'data': t.symbol,
                'relativeUrl':t.relativeUrl
                } for t in tradesignals]
    return render_template(
        'tradesignals.html',
        tradesignals = jsonpickle.encode(tradesignals, unpicklable=False),
        error_message=error_message,
        timeframe=tf,
        indicator=indicator,
        overlay_indicator=overlay_indicator,
        charts=jsonpickle.encode(charts, unpicklable=False),
    )

@app.route('/tradesignals/<date>/<timeframe>', methods=['POST'])
def post_tradesignals(date, timeframe):
    repository.create_tradesignals(date, timeframe, request.get_json())
    return redirect('/')

@app.route('/tradesync', methods=['GET', 'POST'])
def uploadFile():
    if request.method == 'POST':
        f = request.files.get('file')
        repository.process_tradesync(f)
        repository.sync_journal_with_trades()
        
        return render_template('tradesync.html', message="Processed successfully")
    return render_template("tradesync.html", message=None)

@app.route('/crawl', methods=['GET'])
def crawl():
    query = request.args.get('q', None)
    urls = []
    if query:
        journalentries=repository.get_journalentries_forview()
        journalentrygroups=repository.get_journalentrygroups_forview(journalentries)
        tocrawl = filter(lambda x: x.name.find(query) != -1, journalentrygroups)
        for jg in tocrawl:
            urls.append(url_for('viewgroup', key=jg.key))
            for je in jg.deserialized_items:
                if not je.is_group() and not je.is_option():
                    urls.append(url_for('charts', key=je.key))
    return render_template("crawlurls.html", urls=urls)

@app.template_filter('formatdatetimeinput')
def format_datetime(value, format="%Y-%m-%dT%H:%M"):
    if value is None:
        return ""
    if value == toIST_fromtimestamp(0):
        return ""
    return value.strftime(format)


@app.template_filter('formatdatetimedisplay')
def format_datetime(value, format="%d-%m-%Y %I:%M %p"):
    if value is None:
        return ""
    now = IST_now()
    if value == toIST_fromtimestamp(0):
        return ""
    if now.year == value.year:
        return value.strftime("%h %d, %I:%M %p")
    else:
        return value.strftime(format)

@app.template_filter('formatdatetimed3')
def format_datetime(value, format="%Y-%m-%d %H:%M:%S"):
    if value is None:
        return ""
    return value.strftime(format)

@app.template_filter('formatdateonly')
def format_dateonly(value, format="%d-%m-%Y"):
    if value is None:
        return ""
    now = IST_now()
    if value == toIST_fromtimestamp(0):
        return ""
    if now.year == value.year:
        return value.strftime("%d-%m")
    else:
        return value.strftime("%d-%m-%Y")

@app.template_filter('formatfloat')
def format_float(value):
    return round(value, 2)
