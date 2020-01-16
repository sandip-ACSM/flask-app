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
	avg_num_invoice_per_month, avg_invoice_val, month_end_skew FROM 
	company_profile where time_bucket='2017';'''
	cursor.execute(query)
	results = cursor.fetchall()[0]
	params['year'] = 2017
	if request.method=='POST':
		time_bucket_type = request.form['year']
		query = '''SELECT num_territories, num_customers, sale_val, 
		avg_num_invoice_per_month, avg_invoice_val, month_end_skew FROM 
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
		fig = create_bar_plot(x, y, xlabel, ylabel, title,ylimit=(0, 25),\
							  width=0.5, rotation=30, text_offset=0.05)
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
		fig = create_bar_plot(x, y, xlabel, ylabel, title,ylimit=(5, 14),\
							  width=0.5, rotation=30, text_offset=0.05)
		output = io.BytesIO()
		FigureCanvas(fig).print_png(output)
		return Response(output.getvalue(), mimetype='image/png')

	elif graph_name == 'avg_invoice_num': 
		query = '''SELECT territory_name, avg_num_invoice_per_month FROM territory_profile 
		where time_bucket='{}' and time_bucket_type='year' order by avg_num_invoice_per_month desc;
		'''.format(params['year'])
		cursor.execute(query)
		results = cursor.fetchall()
		[x,y] = list(zip(*results))
		xlabel, ylabel = 'Territory', 'Avg. number of invoices/month'
		title = 'Territory-wise avg. number of invoices/month'
		fig = create_bar_plot(x, y, xlabel, ylabel, title, ylimit=(60, 110),\
							  width=0.5, rotation=30, text_offset=0.5)
		output = io.BytesIO()
		FigureCanvas(fig).print_png(output)
		return Response(output.getvalue(), mimetype='image/png')


	elif graph_name == 'avg_invoice_val': 
		query = '''SELECT territory_name, avg_invoice_val FROM territory_profile 
		where time_bucket='{}' and time_bucket_type='year' order by avg_invoice_val desc;
		'''.format(params['year'])
		cursor.execute(query)
		results = cursor.fetchall()
		[x,y] = list(zip(*results))
		xlabel, ylabel = 'Territory', 'Average invoice value'
		title = 'Territory-wise average invoice value'
		fig = create_bar_plot(x, y, xlabel, ylabel, title, ylimit=(88000, 102500),\
							  width=0.5, rotation=30, text_offset=100)
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
		fig = create_bar_plot(x, y, xlabel, ylabel, title,ylimit=(40, 46),\
							  width=0.5, rotation=30, text_offset=0.1)
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
	# global_data['sales'] = {}
	cursor = db.cursor()
	for year in global_data['year_list']:
		query_overall = '''select sale_val from company_profile where 
		time_bucket='{}';'''.format(year)
		cursor.execute(query_overall)
		# global_data['sales'][year] = cursor.fetchall()[0][0]
		total_sale = cursor.fetchall()[0][0]
		query_territory = '''
		select territory_name, sale_val*100/{} from territory_profile where 
		time_bucket='{}' order by sale_val desc limit 3;'''.format(total_sale, year)
		cursor.execute(query_territory)
		results['territory'][year] = cursor.fetchall()

		query_customer = '''
		select customer_name, sale_val*100/{} from customer_profile where 
		time_bucket='{}' order by sale_val desc limit 3;'''.format(total_sale, year)
		cursor.execute(query_customer)
		results['customer'][year] = cursor.fetchall()

		query_sku = '''
		select sku_name, sale_val*100/{} from sku_profile where 
		time_bucket='{}' order by sale_val desc limit 3;'''.format(total_sale, year)
		cursor.execute(query_sku)
		results['sku'][year] = cursor.fetchall()
		
	global_data['top_contribution'] = results
	# print(global_data['top_contribution'])
	return render_template('top_contribution.html', params=params, results=results,\
							year_list=global_data['year_list'])


@app.route("/top_contribution/<string:graph_name>.png", methods=['GET'])
def top_contribution_plot_graph(graph_name):
	year = graph_name[:4]
	entity = graph_name[5:-2]
	rank = int(graph_name[-1])

	cursor = db.cursor()
	query = '''
	select num_territories, num_customers, num_skus from company_profile where time_bucket='2017'; 
	'''
	cursor.execute(query)
	entity_num = cursor.fetchall()[0]

	if rank != 0:
		# Month-wise analysis
		entity_name = global_data['top_contribution'][entity][year][rank-1][0]

		cursor = db.cursor()
		query = '''
		select time_bucket, sale_val from {}_profile where time_bucket_type='month' 
		and {}_name='{}';
		'''.format(entity, entity, entity_name)
		cursor.execute(query)
		month_list_results = cursor.fetchall()
		
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
		title = f'Month-wise sales of {entity_name} in calender year-{year}\n'
		fig = create_line_plot(x, y, xlabel, ylabel,'bD--',title,\
							text_offset=max(y)/40)
	elif rank == 0:
		# Overall analysis in pie chart
		[x,y] = zip(*global_data['top_contribution'][entity][year])
		x = list(x)
		y = [round(a,2) for a in y]
		others_percent = round(100-sum(y), 2)
		if entity == 'territory':
			x.append('Other {} territories'.format(entity_num[0]-3))
		elif entity == 'customer':
			x.append('Other {} customers'.format(entity_num[1]-3))
		elif entity == 'sku':
			x.append('Other {} skus'.format(entity_num[2]-3))
		y.append(others_percent)
		title = f'Pie-diagram for sales of {entity} in calender year-{year}'
		fig = create_pie_plot(x, y, (0.1, 0.1, 0.1, 0), title)
	output = io.BytesIO()
	FigureCanvas(fig).print_png(output)
	return Response(output.getvalue(), mimetype='image/png')

@app.route("/cagr", methods=['GET', 'POST'])
def cagr():
	cagr_result = {}
	overall_query = '''
	select time_bucket, sale_val from company_profile where time_bucket_type='month';
	'''
	overall_df = pd.read_sql(overall_query, db)
	cagr_result['overall'] = calculate_cagr(overall_df)

	territory_query = '''
	select territory_name, time_bucket, sale_val from territory_profile where 
	time_bucket_type='month';
	'''
	territory_df = pd.read_sql(territory_query, db)
	territory_list = territory_df['territory_name'].drop_duplicates(keep='first').tolist()
	for territory in territory_list:
		df = territory_df.loc[territory_df['territory_name']==territory,:]
		cagr_result[territory] = calculate_cagr(df)
	cagr_result = {k: v for k, v in sorted(cagr_result.items(), \
						key=lambda item: item[1], reverse=True)}
	global_data['cagr'] = cagr_result
	territory_list_sorted = list(cagr_result.keys())
	territory_list_sorted.remove('overall')
	return render_template('cagr.html', params=params, cagr_result=cagr_result, 
							territory_list=territory_list_sorted)

@app.route("/cagr/plot.png", methods=['GET'])
def cagr_plot():
	x,y = list(global_data['cagr'].keys()), list(global_data['cagr'].values())
	xlabel, ylabel = 'Territory', 'CAGR (%)'
	title = f'Territory-wise CAGR (%)'
	fig = create_bar_plot(x, y, xlabel, ylabel, title, ylimit=(26, 29),\
							width= 0.5, rotation=30, text_offset=0.05)
	output = io.BytesIO()
	FigureCanvas(fig).print_png(output)
	return Response(output.getvalue(), mimetype='image/png')

@app.route("/top_growing_sales", methods=['GET', 'POST'])
def hotop_growing_salesme():
	return render_template('top_growing_sales.html', params=params)


@app.route("/top_steady_sales", methods=['GET', 'POST'])
def top_steady_sales():
	return render_template('top_steady_sales.html', params=params)


@app.route("/top_declining_sales", methods=['GET', 'POST'])
def top_declining_sales():
	return render_template('top_declining_sales.html', params=params)


def create_bar_plot(x, y, xlabel, ylabel, title, ylimit=(),\
                    width=0.8, rotation=0, bottom=0,text_offset=0):
	fig = plt.figure(figsize=(12,8), dpi=100)
	ax = fig.add_subplot(111)
	xrange = list(range(len(x)))
	plt.bar(xrange, y, width=width, align='center')
	plt.xticks(xrange, x, fontsize=14, rotation=rotation)
	plt.yticks(fontsize=14)
	plt.xlabel(xlabel, fontsize=14);
	plt.ylabel(ylabel, fontsize=14)
	plt.title(title, fontsize=15)
	plt.grid(linestyle = '--', linewidth = 0.15, color = 'k')
	if len(ylimit) !=0:
		plt.ylim(ylimit[0], ylimit[1])
	for i, j in enumerate(y):
			ax.text(i, j+text_offset, j, fontsize=15, ha='center')
	plt.tight_layout()
	ax.spines['top'].set_visible(False)
	ax.spines['right'].set_visible(False)
	# ax.spines['bottom'].set_visible(False)
	ax.spines['left'].set_visible(False)
	return fig


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


def create_pie_plot(x, y, explode, title):
	fig = plt.figure(figsize=(12,8), dpi=100)
	ax = fig.add_subplot(111)
	colors=['dodgerblue', 'yellowgreen', 'plum', 'tomato']
	ax.pie(y, explode=explode, labels=x, autopct='%1.2f%%', colors=colors,
		shadow=True, startangle=0, textprops={'size': 'x-large'})
	ax.axis('equal')
	plt.title(title, fontsize=17)
	return fig


def calculate_cagr(df):
	df['year'] = df.apply(lambda x: int(x['time_bucket'][:4]), axis=1)
	df['month'] = df.apply(lambda x: int(x['time_bucket'][5:]), axis=1)
	df.sort_values(by=['year','month'], inplace=True)
	L = len(df)
	remainder = L%6
	num_six_months = math.floor(L/6)
	df1 = df[:-remainder]
	first_six_months_sale = sum(df1['sale_val'].tolist()[:6])
	last_six_months_sale = sum(df1['sale_val'].tolist()[-6:])

	cagr = (last_six_months_sale/first_six_months_sale)**(1/(0.5*num_six_months))-1
	return round(cagr*100,2)


if __name__ == '__main__':
	app.run(debug=True)