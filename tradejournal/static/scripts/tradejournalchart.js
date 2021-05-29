function TJChart()
{
    funtion Setup(symbol, charts, trades, timeframe)
    {
        var dataWindowSize = 250;
        var windowW = Math.round(window.innerWidth*0.81);
        var windowH = Math.round(window.innerHeight*0.70);
        var currentScrip = "";

        var dim = {
            width: windowW, height: windowH,
            margin: { top: 10, right: 0, bottom: 50, left: 0 },
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
        var parseDate = d3.timeParse("%Y-%m-%d %H:%M:%S");

        var x = techan.scale.financetime()
                .range([0, dim.plot.width]);

        var y = d3.scaleLinear()
                .range([dim.ohlc.height, 0]);

        var yVolume = d3.scaleLinear()
                .range([y(0), y(0.2)]);

        var plotHeikenAshi = false;

        if (!plotHeikenAshi)
        {
            var candlestick = techan.plot.candlestick()
                    .xScale(x)
                    .yScale(y);
        }
        else
        {
            var candlestick = techan.plot.heikinashi()
                    .xScale(x)
                    .yScale(y);

            var heikinashiIndicator = techan.indicator.heikinashi();
        }

        var g_indicator = "{{ indicator }}";
        var g_primaryIndicator = "{{overlay_indicator if not not overlay_indicator else 'ichimoku'}}";

        if (g_primaryIndicator == "ichimoku") {
            var ichimoku = techan.plot.ichimoku()
                .xScale(x)
                .yScale(y);
        }
        else {
            var bollinger = techan.plot.bollinger()
                .xScale(x)
                .yScale(y);
        }

        var xAxis = d3.axisBottom(x);

        var yAxis = d3.axisLeft(y)
                .tickFormat(d3.format(",.3s"));

        var volumeAxis = d3.axisRight(yVolume)
                .ticks(3)
                .tickFormat(d3.format(",.3s"));

        var svg = d3.select("#chart").append("svg")
                .attr("width", windowW)
                .attr("height", windowH)
            .append("g")
                .attr("transform", "translate(" + dim.margin.left + "," + dim.margin.top + ")");

        var defs = svg.append("defs");

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
                .attr("id", function(d, i) { return "indicatorClip-" + i; })
            .append("rect")
                .attr("x", 0)
                .attr("y", function(d, i) { return indicatorTop(i); })
                .attr("width", dim.plot.width)
                .attr("height", dim.indicator.height);


        var indicatorScale = d3.scaleLinear()
                .range([indicatorTop(0)+dim.indicator.height, indicatorTop(0)]);

                if (g_indicator == "stochastic") {
                    var stochastic = techan.plot.stochastic()
                        .xScale(x)
                        .yScale(indicatorScale);

                    var stochasticIndicator = techan.indicator.stochastic()
                }
                else {
                    var macd = techan.plot.macd()
                        .xScale(x)
                        .yScale(indicatorScale);

                    var macdIndicator = techan.indicator.macd()
                }
        var indicatorAxisLeft = d3.axisLeft(indicatorScale)
                .ticks(3);

        var indicatorAnnotationLeft = techan.plot.axisannotation()
                .axis(indicatorAxisLeft)
                .orient("left")
                .format(d3.format(',.2f'));

        var indicatorSelection = svg.selectAll("svg > g.indicator").data(["indicator"]).enter()
                 .append("g")
                 .attr("class", function (d) { return d; });

        indicatorSelection.append("g")
                .attr("class", "axis right")
                .attr("transform", "translate(" + x(1) + ",0)");

        indicatorSelection.append("g")
                .attr("class", "axis left")
                .attr("transform", "translate(" + x(0) + ",0)");

        indicatorSelection.append("g")
                .attr("class", "indicator-plot")
                .attr("clip-path", function(d, i) { return "url(#indicatorClip-" + i + ")"; });

        if (g_primaryIndicator == "ichimoku") {
            var ichimokuIndicator = techan.indicator.ichimoku();
            // Don't show where indicators don't have data
            var indicatorPreRoll = ichimokuIndicator.kijunSen() + ichimokuIndicator.senkouSpanB();
        } else {
            var bollingerIndicator = techan.indicator.bollinger();
        }

        var volume = techan.plot.volume()
                .accessor(candlestick.accessor())   // Set the accessor to a ohlc accessor so we get highlighted bars
                .xScale(x)
                .yScale(yVolume);

        var tradearrow = techan.plot.tradearrow()
            .xScale(x)
            .yScale(y)
            .orient(function(d) { return d.type.startsWith("buy") ? "up" : "down"; })

        svg.append("g")
            .attr("class", g_primaryIndicator)
            .attr("clip-path", "url(#ohlcClip)");

        svg.append("g")
                .attr("class", "candlestick")
                .attr("clip-path", "url(#ohlcClip)");

        svg.append("g")
                .attr("class", "x axis")
                .attr("transform", "translate(0," + dim.indicator.bottom + ")");

        svg.append("g")
                .attr("class", "y axis")
            .append("text")
                .attr('id', 'charttitle')
                .attr("transform", "rotate(-90)")
                .attr("y", 6)
                .attr("dy", ".71em")
                    .style("text-anchor", "end")
                {%if journalentry %}
            .text("{{journalentry.symbol}}({{timeframe}})");
                {%endif%}
        svg.append("g")
                .attr("class", "volume")
                .attr("clip-path", "url(#ohlcClip)");

        svg.append("g")
                  .attr("class", "tradearrow")
                    .attr("clip-path", "url(#ohlcClip)");
    }

    function draw(data) {
        if (plotHeikenAshi)
        {
            candlestickData = heikinashiIndicator(data);
        }
        else
        {
            candlestickData = data;
        }

        if (g_primaryIndicator == "ichimoku") {
            var ichimokuData = ichimokuIndicator(data);
            x.domain(data.map(ichimokuIndicator.accessor().d));
            // Calculate the y domain for visible data points (ensure to include Kijun Sen additional data offset)
            var y_domain = techan.scale.plot.ichimoku(ichimokuData.slice(indicatorPreRoll - ichimokuIndicator.kijunSen())).domain();
            y_domain = [y_domain[0] * 0.95, y_domain[1] * 1.05];
            y.domain(y_domain);
            yVolume.domain(techan.scale.plot.volume(data.slice(indicatorPreRoll - ichimokuIndicator.kijunSen())).domain());

            // Logic to ensure that at least +KijunSen displacement is applied to display cloud plotted ahead of ohlc
            x.zoomable().clamp(false).domain([indicatorPreRoll, data.length + ichimokuIndicator.kijunSen()]);
            svg.selectAll("g.ichimoku").datum(ichimokuData).call(ichimoku);
        } else {
            var bollingerData = bollingerIndicator(data);
            x.domain(bollingerData.map(bollingerIndicator.accessor().d));
            y.domain(techan.scale.plot.bollinger(bollingerData).domain());
            yVolume.domain(techan.scale.plot.volume(data).domain());
            svg.selectAll("g.bollinger").datum(bollingerData).call(bollinger);

        }
        svg.selectAll("g.candlestick").datum(candlestickData).call(candlestick);
        svg.selectAll("g.x.axis").call(xAxis);
        svg.selectAll("g.y.axis").call(yAxis);
        svg.selectAll("g.volume").datum(data).call(volume);

        if (g_indicator == "stochastic") {
            var stochasticData = stochasticIndicator(data);
            indicatorScale.domain(techan.scale.plot.stochastic(stochasticData).domain());
            svg.selectAll("g.indicator .indicator-plot").datum(stochasticData).call(stochastic);
        }
        else {
            var macdData = macdIndicator(data);
            indicatorScale.domain(techan.scale.plot.macd(macdData).domain());
            svg.selectAll("g.indicator .indicator-plot").datum(macdData).call(macd);
        }
        svg.selectAll("g.indicator .axis.left").call(indicatorAxisLeft);

        if (trades.length == 2 && trades[1].date > data[data.length - 1].date) {
            chartTrades = [...trades].splice(0, 1);
        }
        else {
            chartTrades = trades;
        }
        svg.selectAll("g.tradearrow").selectAll("*").remove();
        svg.selectAll("g.tradearrow").datum(chartTrades).call(tradearrow);
    }

            var charts = JSON.parse('{{ charts | safe}}');
            var g_timeFrame = '{{ timeframe }}';
            var g_resampleType = 'original';

        function RenderChart(i, timeFrame, resampleType=null) {
            if (i >= charts.length) 
            {
                    return;
            }

            document.getElementById('title').innerText = charts[i].title + " (" + (i+1) + " of " + charts.length + ")";
            {%if not journalentry%}
            document.getElementById('charttitle').innerHTML = charts[currentChartIndex].data + ' (' + timeFrame[1].toUpperCase() + ')';
            {%endif%}
            document.getElementById('main').hidden = false;
            function D3_DataCallback(error, data) {
                charts[i].raw_data = data;
                data = data.map(function (d) {
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
                if (dataWindowSize < data.length) {
                    data = data.slice(data.length - dataWindowSize, data.length)
                }
                draw(data);
            }
            if (charts[i].raw_data == null) {
                var temp = charts[i].relativeUrl.split('?');
                params = new URLSearchParams(temp[1]);
                params.set('tf', timeFrame);
                if (resampleType) {
                    params.set('type', resampleType);
                }
                relativeUrl = temp[0] + '?' + params;
                d3.csv(relativeUrl, D3_DataCallback)
            } else {
                D3_DataCallback(null, charts[i].raw_data);
            }
        }

        var currentChartIndex = 0;
        if (charts.length > 0) {
                currentChartIndex = charts.length - 1;
            RenderChart(currentChartIndex, g_timeFrame, g_resampleType);
        }
        else {
            document.getElementById('title').innerText = "No charts available";
            document.getElementById('main').hidden = true;
            }

        function RenderCurrentChart(timeFrame, resampleType=null) {
            charts[currentChartIndex].raw_data = null;
            RenderChart(currentChartIndex, timeFrame, resampleType);
        }

        function RenderNextChart() {
            currentChartIndex++;
            if (currentChartIndex >= charts.length)
                currentChartIndex = 0;
            if (charts.length > 0)
                RenderChart(currentChartIndex, g_timeFrame, g_resampleType);
        }

        function RenderPreviousChart() {
            currentChartIndex--;
            if (currentChartIndex < 0)
                currentChartIndex = charts.length-1;
            if (charts.length > 0)
                RenderChart(currentChartIndex, g_timeFrame, g_resampleType);
            }

        function ToggleIndicator() {
            oind = g_primaryIndicator == "bollinger" ? "ichimoku" : "bollinger";
            params = new URLSearchParams(window.location.search);
            params.set('oind', oind);
            newUrl = window.location.origin + window.location.pathname + '?' + params;
            window.location.href = newUrl;
        }

        {%if journalentry%}
            function DeleteCurrentChart() {
                $.ajax({
                    url: 'charts/' + charts[currentChartIndex].key + '/delete',
                    type: 'DELETE',
                    success: function(result) {
                        window.location.reload();
                    }
                });
            }
        {%endif%}
}
