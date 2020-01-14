from flask import Flask, render_template, request, session, redirect, Response
from flask_sqlalchemy import SQLAlchemy
from werkzeug import secure_filename
import json
import os
import math
from datetime import datetime
import pymysql
import pandas as pd
import io
import random
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure


with open('config.json', 'r') as c:
	params = json.load(c)["params"]

app = Flask(__name__)
# app.secret_key = '1253246754467'
app.config['UPLOAD_FOLDER'] = params['upload_location']
# app.config['SQLALCHEMY_DATABASE_URI'] = params['database_uri']
# db = SQLAlchemy(app)

db = pymysql.connect(params["endpoint"], params["username"], \
					 params["password"], params["db_name"])


@app.route("/", methods=['GET', 'POST'])
def home():
	results = {}
	cursor = db.cursor()

	query = '''SELECT num_territories, num_customers, sale_val, 
	avg_num_invoice_per_month, month_end_skew FROM 
	company_profile where time_bucket='2017';'''
	cursor.execute(query)
	results = cursor.fetchall()[0]
	params['year'] = 2017
	if request.method=='POST':
		time_bucket_type = request.form['year']
		query = '''SELECT num_territories, num_customers, sale_val, 
		avg_num_invoice_per_month, month_end_skew FROM 
		company_profile where time_bucket='{}';'''.format(time_bucket_type)
		cursor.execute(query)
		results = cursor.fetchall()[0]
		params['year'] = time_bucket_type
	return render_template('index.html', params=params, results=results)


@app.route("/<string:graph_name>.png", methods=['GET', 'POST'])
def home_plot_graph(graph_name):
	if graph_name == 'skew':
		fig = create_line_plot()
		output = io.BytesIO()
		FigureCanvas(fig).print_png(output)
		return Response(output.getvalue(), mimetype='image/png')


@app.route("/seasonality", methods=['GET', 'POST'])
def seasonality():
	return render_template('seasonality.html', params=params)


@app.route("/cagr", methods=['GET', 'POST'])
def cagr():
	return render_template('cagr.html', params=params)


@app.route("/top_contribution", methods=['GET', 'POST'])
def top_contribution():
	return render_template('top_contribution.html', params=params)


@app.route("/top_growing_sales", methods=['GET', 'POST'])
def hotop_growing_salesme():
	return render_template('top_growing_sales.html', params=params)


@app.route("/top_steady_sales", methods=['GET', 'POST'])
def top_steady_sales():
	return render_template('top_steady_sales.html', params=params)


@app.route("/top_declining_sales", methods=['GET', 'POST'])
def top_declining_sales():
	return render_template('top_declining_sales.html', params=params)


def create_bar_plot():
    fig = Figure()
    axis = fig.add_subplot(1, 1, 1)
    xs = range(100)
    ys = [random.randint(1, 50) for x in xs]
    axis.plot(xs, ys)
    return fig

def create_line_plot():
    fig = Figure()
    axis = fig.add_subplot(1, 1, 1)
    xs = range(100)
    ys = [random.randint(1, 50) for x in xs]
    axis.plot(xs, ys)
    return fig

if __name__ == '__main__':
	app.run(debug=True)