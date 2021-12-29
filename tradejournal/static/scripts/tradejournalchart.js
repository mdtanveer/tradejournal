class TJChart
{
    constructor(key, symbol, charts, trades, timeframe, primaryIndicator, secondaryIndicator, eventTargets=null)
    {
        this.key = key;
        this.symbol = symbol;
        this.charts = charts;
        this.timeFrame = timeframe;
        this.resampleType = 'original';
        this.secondaryIndicator = secondaryIndicator;
        this.primaryIndicator = primaryIndicator;
        this.trades = trades;
        if(symbol)
            this.currentChartIndex = charts.length - 1;
        else
            this.currentChartIndex = 0;
        this.eventTargets=eventTargets;
        this.DispatchCurrentIndexChanged();

        this.dataWindowSize = 250;
        var windowW = document.getElementById("main").clientWidth;
        //var windowW = Math.round(window.innerWidth*0.81);
        var windowH = Math.round(window.innerHeight*0.60);
        var currentScrip = "";

        var dim = {
            width: windowW, height: windowH,
            margin: { top: 10, right: 10, bottom: 40, left: 40 },
            ohlc: { height: 305 },
            indicator: { height: 65, padding: 5 }
        };


        dim.plot = {
            width: dim.width - dim.margin.left - dim.margin.right,
            height: dim.height - dim.margin.top - dim.margin.bottom
        };
        dim.ohlc.height = Math.floor(dim.plot.height*0.80)
        dim.indicator.height = Math.floor(dim.plot.height*0.20)

        dim.indicator.top = dim.ohlc.height+dim.indicator.padding;
        dim.indicator.bottom = dim.indicator.top+dim.indicator.height+dim.indicator.padding;

        var indicatorTop = d3.scaleLinear()
                .range([dim.indicator.top, dim.indicator.bottom]);

        this.x = techan.scale.financetime()
                .range([0, dim.plot.width]);

        this.y = d3.scaleLinear()
                .range([dim.ohlc.height, 0]);

        this.yVolume = d3.scaleLinear()
                .range([this.y(0), this.y(0.2)]);

        this.plotHeikenAshi = false;

        if (!this.plotHeikenAshi)
        {
            this.candlestick = techan.plot.candlestick()
                    .xScale(this.x)
                    .yScale(this.y);
        }
        else
        {
            this.candlestick = techan.plot.heikinashi()
                    .xScale(this.x)
                    .yScale(this.y);

            this.heikinashiIndicator = techan.indicator.heikinashi();
        }


        if (this.primaryIndicator == "ichimoku") {
            this.ichimoku = techan.plot.ichimoku()
                .xScale(this.x)
                .yScale(this.y);
        }
        else {
            this.bollinger = techan.plot.bollinger()
                .xScale(this.x)
                .yScale(this.y);
        }

        this.xAxis = d3.axisBottom(this.x);

        this.yAxis = d3.axisLeft(this.y)
                .tickFormat(d3.format(",.3s"));

        var volumeAxis = d3.axisRight(this.yVolume)
                .ticks(3)
                .tickFormat(d3.format(",.3s"));

        this.svg = d3.select("#chart").append("svg")
                .attr("width", windowW)
                .attr("height", windowH)
            .append("g")
                .attr("transform", "translate(" + dim.margin.left + "," + dim.margin.top + ")");

        var defs = this.svg.append("defs");

        defs.append("clipPath")
                .attr("id", "ohlcClip")
                .append("rect")
                .attr("x", 0)
                .attr("y", 0)
                .attr("width", dim.plot.width)
                .attr("height", dim.ohlc.height);

        defs.selectAll("indicatorClip").data([0])
            .enter()
                .append("clipPath")
                .attr("id", function(d, i) { return "indicatorClip-" + i })
            .append("rect")
                .attr("x", 0)
                .attr("y", function(d, i)  { return indicatorTop(i); })
                .attr("width", dim.plot.width)
                .attr("height", dim.indicator.height);


        this.indicatorScale = d3.scaleLinear()
                .range([indicatorTop(0)+dim.indicator.height, indicatorTop(0)]);

                if (this.secondaryIndicator == "stochastic") {
                    this.stochastic = techan.plot.stochastic()
                        .xScale(this.x)
                        .yScale(this.indicatorScale);

                    this.stochasticIndicator = techan.indicator.stochastic()
                }
                else {
                    this.macd = techan.plot.macd()
                        .xScale(this.x)
                        .yScale(this.indicatorScale);

                    this.macdIndicator = techan.indicator.macd()
                }
        this.indicatorAxisLeft = d3.axisLeft(this.indicatorScale)
                .ticks(3);

        var indicatorAnnotationLeft = techan.plot.axisannotation()
                .axis(this.indicatorAxisLeft)
                .orient("left")
                .format(d3.format(',.2f'));

        var indicatorSelection = this.svg.selectAll("svg > g.indicator").data(["indicator"]).enter()
                 .append("g")
                 .attr("class", function (d) { return d; });

        indicatorSelection.append("g")
                .attr("class", "axis right")
                .attr("transform", "translate(" + this.x(1) + ",0)");

        indicatorSelection.append("g")
                .attr("class", "axis left")
                .attr("transform", "translate(" + this.x(0) + ",0)");

        indicatorSelection.append("g")
                .attr("class", "indicator-plot")
                .attr("clip-path", function(d, i) { return "url(#indicatorClip-" + i + ")"; });

        if (this.primaryIndicator == "ichimoku") {
            this.ichimokuIndicator = techan.indicator.ichimoku();
            // Don't show where indicators don't have data
            this.indicatorPreRoll = this.ichimokuIndicator.kijunSen() + this.ichimokuIndicator.senkouSpanB();
        } else {
            this.bollingerIndicator = techan.indicator.bollinger();
        }

        if (this.timeFrame == "2h" || this.timeframe == "1h") {
            var annotationFormat = d3.timeFormat('%m-%d %H:%M')
        } else {
            var annotationFormat = d3.timeFormat('%m-%d')
        }

        var timeAnnotation = techan.plot.axisannotation()
            .axis(this.xAxis)
            .orient('bottom')
            .format(annotationFormat)
            .width(65)
            .translate([0, dim.indicator.bottom]);

        var ohlcAnnotation = techan.plot.axisannotation()
            .axis(this.yAxis)
            .orient('left')
            .format(d3.format('.4s'))
            .translate([this.x(0), 0]);

        this.ohlcCrosshair = techan.plot.crosshair()
            .xScale(timeAnnotation.axis().scale())
            .yScale(ohlcAnnotation.axis().scale())
            .xAnnotation(timeAnnotation)
            .yAnnotation([ohlcAnnotation])
            .verticalWireRange([0, dim.plot.height]);

        this.supstance = techan.plot.supstance()
            .xScale(this.x)
            .yScale(this.y);

        this.volume = techan.plot.volume()
                .accessor(this.candlestick.accessor())   // Set the accessor to a ohlc accessor so we get highlighted bars
                .xScale(this.x)
                .yScale(this.yVolume);

        this.tradearrow = techan.plot.tradearrow()
            .xScale(this.x)
            .yScale(this.y)
            .orient(function(d) { return d.type.startsWith("buy") ? "up" : "down"; })

        this.svg.append("g")
            .attr("class", this.primaryIndicator)
            .attr("clip-path", "url(#ohlcClip)");

        this.svg.append("g")
                .attr("class", "candlestick")
                .attr("clip-path", "url(#ohlcClip)");

        this.svg.append("g")
                .attr("class", "x axis")
                .attr("transform", "translate(0," + dim.indicator.bottom + ")");

        this.svg.append("g")
                .attr("class", "y axis")
                .append("text")
                .attr('id', 'charttitle')
                .attr("transform", "rotate(-90)")
                .attr("y", 6)
                .attr("dy", ".71em")
                .style("text-anchor", "end")
                .text(symbol + '(' + timeframe + ')');
        this.svg.append("g")
                .attr("class", "volume")
                .attr("clip-path", "url(#ohlcClip)");

        this.svg.append("g")
                  .attr("class", "tradearrow")
                    .attr("clip-path", "url(#ohlcClip)");

        this.svg.append('g')
            .attr("class", "crosshair ohlc");

        this.svg.append("g")
            .attr("class", "supstances analysis")
            .attr("clip-path", "url(#ohlcClip)");    
    }

    draw(data) {
        if (this.plotHeikenAshi)
        {
            var candlestickData = this.heikinashiIndicator(data);
        }
        else
        {
            var candlestickData = data;
        }

        if (this.primaryIndicator == "ichimoku") {
            var ichimokuData = this.ichimokuIndicator(data);
            this.x.domain(data.map(this.ichimokuIndicator.accessor().d));
            // Calculate the y domain for visible data points (ensure to include Kijun Sen additional data offset)
            var y_domain = techan.scale.plot.ichimoku(ichimokuData.slice(this.indicatorPreRoll - this.ichimokuIndicator.kijunSen())).domain();
            y_domain = [y_domain[0] * 0.95, y_domain[1] * 1.05];
            this.y.domain(y_domain);
            this.yVolume.domain(techan.scale.plot.volume(data.slice(this.indicatorPreRoll - this.ichimokuIndicator.kijunSen())).domain());

            // Logic to ensure that at least +KijunSen displacement is applied to display cloud plotted ahead of ohlc
            this.x.zoomable().clamp(false).domain([this.indicatorPreRoll, data.length + this.ichimokuIndicator.kijunSen()]);
            this.svg.selectAll("g.ichimoku").datum(ichimokuData).call(this.ichimoku);
        } else {
            var bollingerData = this.bollingerIndicator(data);
            this.x.domain(bollingerData.map(this.bollingerIndicator.accessor().d));
            this.y.domain(techan.scale.plot.bollinger(bollingerData).domain());
            this.yVolume.domain(techan.scale.plot.volume(data).domain());
            this.svg.selectAll("g.bollinger").datum(bollingerData).call(this.bollinger);

        }
        this.svg.selectAll("g.candlestick").datum(candlestickData).call(this.candlestick);
        this.svg.selectAll("g.x.axis").call(this.xAxis);
        this.svg.selectAll("g.y.axis").call(this.yAxis);
        this.svg.selectAll("g.volume").datum(data).call(this.volume);

        if (this.secondaryIndicator == "stochastic") {
            var stochasticData = this.stochasticIndicator(data);
            this.indicatorScale.domain(techan.scale.plot.stochastic(stochasticData).domain());
            this.svg.selectAll("g.indicator .indicator-plot").datum(stochasticData).call(this.stochastic);
        }
        else {
            var macdData = this.macdIndicator(data);
            this.indicatorScale.domain(techan.scale.plot.macd(macdData).domain());
            this.svg.selectAll("g.indicator .indicator-plot").datum(macdData).call(this.macd);
        }
        this.svg.selectAll("g.indicator .axis.left").call(this.indicatorAxisLeft);

        if (this.trades) {
            if (this.trades.length == 2 && this.trades[1].date > data[data.length - 1].date) {
                var chartTrades = [...this.trades].splice(0, 1);
            }
            else {
                var chartTrades = this.trades;
                var supstanceData = [
                    { start: this.trades[0].date, end: this.trades[1].date, value: this.trades[0].price },
                    { start: this.trades[0].date, end: this.trades[1].date, value: this.trades[1].price },
                ];
                //this.svg.select("g.supstances").datum(supstanceData).call(this.supstance)
            }
            this.svg.selectAll("g.tradearrow").selectAll("*").remove();
            this.svg.selectAll("g.tradearrow").datum(chartTrades).call(this.tradearrow);
        }

        this.svg.select("g.crosshair.ohlc").call(this.ohlcCrosshair);
    }


        RenderChart() {
            var i = this.currentChartIndex;
            if (i >= this.charts.length) 
            {
                    return;
            }

            document.getElementById('main').hidden = false;
            
            var selfInstance = this;
            function D3_DataCallback(error, data) {
                selfInstance.charts[i].raw_data = data;
                data = data.map(function (d) {
                    var parseDate = d3.timeParse("%Y-%m-%d %H:%M:%S");
                    // Open, high, low, close generally not required, is being used here to demonstrate colored volume
                    // bars
                    return {
                        date: parseDate(d.date + ' ' + d.time),
                        volume: +d.volume,
                        open: +d.open,
                        high: +d.high,
                        low: +d.low,
                        close: +d.close
                    };
                })
                if (selfInstance.dataWindowSize < data.length) {
                    data = data.slice(data.length - selfInstance.dataWindowSize, data.length)
                }
                selfInstance.draw(data);
                if(selfInstance.symbol == null)
                {
                    document.getElementById('charttitle').innerHTML = selfInstance.charts[i].data + ' (' + selfInstance.timeFrame + ')';
                }
                else
                {
                    document.getElementById('charttitle').innerHTML = selfInstance.charts[i].title + " (" + (i+1) + " of " + selfInstance.charts.length + ") "
                        + selfInstance.symbol + ' (' + selfInstance.timeFrame + ')';
                }
            }

            if (this.charts[i].raw_data == null) {
                var temp = this.charts[i].relativeUrl.split('?');
                var params = new URLSearchParams(temp[1]);
                if(this.timeFrame)
                    params.set('tf', this.timeFrame);
                if (this.resampleType) {
                    params.set('type', this.resampleType);
                }
                var relativeUrl = temp[0] + '?' + params;
                if(this.symbol != null && this.key != null)
                {
                    relativeUrl = "/journalentry/"+this.key+"/"+relativeUrl;
                }
                d3.csv(relativeUrl, D3_DataCallback)
            } else {
                D3_DataCallback(null, this.charts[i].raw_data);
            }
        }

        RenderCurrentChartSwitchTF(timeFrame) {
            this.timeFrame = timeFrame;
            this.charts[this.currentChartIndex].raw_data = null;
            this.RenderChart();
        }

        RenderCurrentChartResampleTF(resampleType) {
            this.resampleType = resampleType;
            this.charts[this.currentChartIndex].raw_data = null;
            this.RenderChart();
        }

        RenderNextChart() {
            this.currentChartIndex++;
            this.DispatchCurrentIndexChanged();
            if (this.currentChartIndex >= this.charts.length)
                this.currentChartIndex = 0;
            if (this.charts.length > 0)
               this.RenderChart();
        }

        RenderPreviousChart() {
            this.currentChartIndex--;
            this.DispatchCurrentIndexChanged();
            if (this.currentChartIndex < 0)
                this.currentChartIndex = this.charts.length-1;
            if (this.charts.length > 0)
                this.RenderChart();
            }

        ToggleIndicator() {
            var oind = this.primaryIndicator == "bollinger" ? "ichimoku" : "bollinger";
            var params = new URLSearchParams(window.location.search);
            params.set('oind', oind);
            var newUrl = window.location.origin + window.location.pathname + '?' + params;
            window.location.href = newUrl;
        }

        DeleteCurrentChart() {
            $.ajax({
                url: '/journalentry/'+this.key+'/'+'charts'+'/' + this.charts[this.currentChartIndex].key + '/delete',
                type: 'DELETE',
                success: function(result) {
                    window.location.reload();
                }
            });
        }

        DispatchCurrentIndexChanged() {
            const cusevent = new CustomEvent('cidxchanged', { detail : this.currentChartIndex });
            for (var i=0; this.eventTargets && i<this.eventTargets.length; i++) {
                this.eventTargets[i].dispatchEvent(cusevent)
            }
        }
        
        SetTrades(trades) {
            this.trades = trades;
        }
}
