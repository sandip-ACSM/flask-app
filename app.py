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
import matplotlib.pyplot as plt


with open('config.json', 'r') as c:
	params = json.load(c)["params"]
global_data = {}

app = Flask(__name__)
# app.secret_key = '1253246754467'
app.config['UPLOAD_FOLDER'] = params['upload_location']
# app.config['SQLALCHEMY_DATABASE_URI'] = params['database_uri']
# db = SQLAlchemy(app)

db = pymysql.connect(params["endpoint"], params["username"], \
					 params["password"], params["db_name"])

year_list_query = '''
	select distinct time_bucket from company_profile where time_bucket_type='year' 
	order by time_bucket;
	'''
cursor1 = db.cursor()
cursor1.execute(year_list_query)
year_list_results = cursor1.fetchall()
global_data['year_list'] = list(zip(*year_list_results))[0]


@app.route("/", methods=['GET', 'POST'])
def home():
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


@app.route("/<string:graph_name>.png", methods=['GET'])
def home_plot_graph(graph_name):
	cursor = db.cursor()
	if graph_name == 'cust_num':
		query = '''SELECT territory_name, num_customers FROM territory_profile 
		where time_bucket='{}' and time_bucket_type='year' order by num_customers desc;
		'''.format(params['year'])
		cursor.execute(query)
		results = cursor.fetchall()
		[x,y] = list(zip(*results))
		xlabel, ylabel = 'Territory', 'Customer number'
		title = 'Territory-wise Customer number'
		fig = create_line_plot(x, y, xlabel, ylabel,'bD--',title,\
							   rotation=30, text_offset=0.05)
		output = io.BytesIO()
		FigureCanvas(fig).print_png(output)
		return Response(output.getvalue(), mimetype='image/png')

	elif graph_name == 'sale':
		query = '''SELECT territory_name, sale_val FROM territory_profile 
		where time_bucket='{}' and time_bucket_type='year' order by sale_val desc;
		'''.format(params['year'])
		cursor.execute(query)
		results = cursor.fetchall()
		[x,y] = list(zip(*results))
		y = [round(a/10000000,2) for a in y]
		xlabel, ylabel = 'Territory', 'Sales (Crores)'
		title = 'Territory-wise sales in Crores'
		fig = create_line_plot(x, y, xlabel, ylabel,'bD--',title,\
							   rotation=30, text_offset=0.05)
		output = io.BytesIO()
		FigureCanvas(fig).print_png(output)
		return Response(output.getvalue(), mimetype='image/png')

	elif graph_name == 'avg_invoice': 
		query = '''SELECT territory_name, avg_num_invoice_per_month FROM territory_profile 
		where time_bucket='{}' and time_bucket_type='year' order by avg_num_invoice_per_month desc;
		'''.format(params['year'])
		cursor.execute(query)
		results = cursor.fetchall()
		[x,y] = list(zip(*results))
		xlabel, ylabel = 'Territory', 'Avg. number of invoices/month'
		title = 'Territory-wise avg. number of invoices/month'
		fig = create_line_plot(x, y, xlabel, ylabel,'bD--',title,\
							   rotation=30, text_offset=0.4)
		output = io.BytesIO()
		FigureCanvas(fig).print_png(output)
		return Response(output.getvalue(), mimetype='image/png')

	elif graph_name == 'skew': 
		query = '''SELECT territory_name, month_end_skew FROM territory_profile 
		where time_bucket='{}' and time_bucket_type='year' order by month_end_skew desc;
		'''.format(params['year'])
		cursor.execute(query)
		results = cursor.fetchall()
		[x,y] = list(zip(*results))
		xlabel, ylabel = 'Territory', 'Month end skew (%)'
		title = 'Territory-wise month end skew in %'
		fig = create_line_plot(x, y, xlabel, ylabel,'bD--',title,\
							   rotation=30, text_offset=0.1)
		output = io.BytesIO()
		FigureCanvas(fig).print_png(output)
		return Response(output.getvalue(), mimetype='image/png')


@app.route("/seasonality", methods=['GET', 'POST'])
def seasonality():
	results = {}
	cursor = db.cursor()
	query = '''select time_bucket, sale_val from 
	company_profile where time_bucket_type='month' order by time_bucket;'''
	cursor.execute(query)
	month_list_results = cursor.fetchall()
	# [month_list, sales_list] = list(zip(*month_list_results))
	
	for year in global_data['year_list']:
		results[year] = {}
		for x,y in (month_list_results):
			if x[:4] == str(year):
				results[year][x[5:]] = round(y/10000000,2)
	global_data['seasonality'] = results
	return render_template('seasonality.html', params=params, results=results,\
							year_list=global_data['year_list'])


@app.route("/seasonality/<string:graph_name>.png", methods=['GET'])
def seasonality_plot_graph(graph_name):
	monthly_sales_dict = global_data['seasonality'][graph_name]
	x,y = list(monthly_sales_dict.keys()), list(monthly_sales_dict.values())
	x = [int(a) for a in x]
	y = [a for _,a in sorted(zip(x,y))]
	# x.sort()
	x = ['APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', \
		 'DEC', 'JAN', 'FEB', 'MAR']
	x = x[:len(y)]
	xlabel, ylabel = 'Month', 'Sales (Crores)'
	title = 'Month-wise plot (APR, {} - MAR, {})'.format(graph_name, int(graph_name)+1)
	fig = create_line_plot(x, y, xlabel, ylabel,'bD--',title,\
						   text_offset=0.3)
	output = io.BytesIO()
	FigureCanvas(fig).print_png(output)
	return Response(output.getvalue(), mimetype='image/png')


@app.route("/top_contribution", methods=['GET', 'POST'])
def top_contribution():
	results = {
		'territory': {},
		'customer': {},
		'sku': {}
	}
	cursor = db.cursor()
	for year in global_data['year_list']:
		query_territory = '''
		select territory_name, sale_val from territory_profile where 
		time_bucket='{}' order by sale_val desc limit 3;'''.format(year)
		cursor.execute(query_territory)
		results['territory'][year] = cursor.fetchall()

		query_customer = '''
		select customer_name, sale_val from customer_profile where 
		time_bucket='{}' order by sale_val desc limit 3;'''.format(year)
		cursor.execute(query_customer)
		results['customer'][year] = cursor.fetchall()

		query_sku = '''
		select sku_name, sale_val from sku_profile where 
		time_bucket='{}' order by sale_val desc limit 3;'''.format(year)
		cursor.execute(query_sku)
		results['sku'][year] = cursor.fetchall()
		
	global_data['top_contribution'] = results
	print(global_data['top_contribution'])
	return render_template('top_contribution.html', params=params, results=results,\
								year_list=global_data['year_list'])


@app.route("/top_contribution/<string:graph_name>.png", methods=['GET'])
def top_contribution_plot_graph(graph_name):
	year = graph_name[:4]
	entity = graph_name[5:-2]
	rank = int(graph_name[-1])

	entity_name = global_data['top_contribution'][entity][year][rank-1][0]

	cursor = db.cursor()
	query = '''
	select time_bucket, sale_val from {}_profile where time_bucket_type='month' 
	and {}_name='{}';
	'''.format(entity, entity, entity_name)
	cursor.execute(query)
	month_list_results = cursor.fetchall()
	# [month_list, sales_list] = list(zip(*month_list_results))
	
	monthly_sales_dict = {}
	for x,y in month_list_results:
		if x[:4] == str(year):
			monthly_sales_dict[x[5:]] = y

	x,y = list(monthly_sales_dict.keys()), list(monthly_sales_dict.values())
	x = [int(a) for a in x]
	y = [a for _,a in sorted(zip(x,y))]
	y = [round(a/10000000,2) for a in y]
	# x.sort()
	x = ['APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', \
		 'DEC', 'JAN', 'FEB', 'MAR']
	x = x[:len(y)]
	xlabel, ylabel = 'Month', 'Sales (Crores)'
	title = 'Top 3'
	fig = create_line_plot(x, y, xlabel, ylabel,'bD--',title,\
						   text_offset=max(y)/40)
	output = io.BytesIO()
	FigureCanvas(fig).print_png(output)
	return Response(output.getvalue(), mimetype='image/png')

@app.route("/cagr", methods=['GET', 'POST'])
def cagr():
	return render_template('cagr.html', params=params)


@app.route("/top_growing_sales", methods=['GET', 'POST'])
def hotop_growing_salesme():
	return render_template('top_growing_sales.html', params=params)


@app.route("/top_steady_sales", methods=['GET', 'POST'])
def top_steady_sales():
	return render_template('top_steady_sales.html', params=params)


@app.route("/top_declining_sales", methods=['GET', 'POST'])
def top_declining_sales():
	return render_template('top_declining_sales.html', params=params)


# def create_bar_plot():
#     fig = Figure()
#     axis = fig.add_subplot(1, 1, 1)
#     xs = range(100)
#     ys = [random.randint(1, 50) for x in xs]
#     axis.plot(xs, ys)
#     return fig

# def create_line_plot():
#     fig = Figure()
#     axis = fig.add_subplot(1, 1, 1)
#     xs = range(100)
#     ys = [random.randint(1, 50) for x in xs]
#     axis.plot(xs, ys)
#     return fig

def create_line_plot(x, y, xlabel, ylabel, linetype, title,
                     xlimit=(), ylimit=(), rotation=0, text_offset=0):
	fig = plt.figure(figsize=(12,8), dpi=100)
	ax = fig.add_subplot(111)
	plt.plot(range(len(x)), y, linetype, linewidth = 1.5)
	plt.xlabel(xlabel, fontsize=14);
	plt.ylabel(ylabel, fontsize=14)
	plt.title(title, fontsize=15)
	plt.grid(linestyle = '--', linewidth = 0.2, color = 'k')
	plt.xticks(range(len(x)), x, fontsize=14, rotation=rotation); 
	plt.yticks(fontsize=14)
	for i, j in enumerate(y):
		ax.text(i, j+text_offset, j, fontsize=15, ha='center')
	if len(xlimit) !=0:
		plt.xlim(xlimit[0], xlimit[1])
	if len(ylimit) !=0:
		plt.ylim(ylimit[0], ylimit[1])
	plt.tight_layout()
	ax.spines['top'].set_visible(False)
	ax.spines['right'].set_visible(False)
	ax.spines['bottom'].set_visible(False)
	ax.spines['left'].set_visible(False)
	return fig

if __name__ == '__main__':
	app.run(debug=True)