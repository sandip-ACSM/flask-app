import os
import io
import math
import json
from datetime import datetime
import pymysql
import numpy as np
import pandas as pd
import random
from flask import Flask, render_template, request, session, redirect, Response
from flask_sqlalchemy import SQLAlchemy
from werkzeug import secure_filename
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import itertools
from configparser import ConfigParser
from utils import *

config = ConfigParser()
config.read('config.ini')

host  = config['database']['endpoint']
username = config['database']['username']
password = config['database']['password']
db_name = config['database']['db_name']

upload_folder = config['upload_folder']['location']

def get_list_from_db(query):
	cursor = db.cursor()
	cursor.execute(query)
	result_list = cursor.fetchall()
	return list(zip(*result_list))[0]

app = Flask(__name__)
global_data = {}
db = pymysql.connect(host, username, password, db_name)

year_list_query = '''
	select distinct time_bucket from company_profile where time_bucket_type='year' 
	order by time_bucket;
	'''
territory_list_query = '''
	select distinct territory_name from territory_profile;
	'''
customer_list_query = '''
	select distinct customer_name from customer_profile;
	'''
sku_list_query = '''
	select distinct sku_name from sku_profile;
	'''
global_data['year_list'] = get_list_from_db(year_list_query)
global_data['territory_list'] = get_list_from_db(territory_list_query)
global_data['customer_list'] = get_list_from_db(customer_list_query)
global_data['sku_list'] = get_list_from_db(sku_list_query)


@app.route("/", methods=['GET', 'POST'])
def home():
	cursor = db.cursor() 
	current_year = global_data['year_list'][-1]
	query = '''SELECT num_territories, num_customers, sale_val, 
		avg_num_invoice_per_month, avg_invoice_val, percent_sale_subperiod_4 FROM 
		company_profile where time_bucket='{}';'''.format(current_year)
	cursor.execute(query)
	if request.method=='POST':
		current_year = request.form['year']
		query = '''SELECT num_territories, num_customers, sale_val, 
		avg_num_invoice_per_month, avg_invoice_val, percent_sale_subperiod_4 FROM 
		company_profile where time_bucket='{}';'''.format(current_year)
		cursor.execute(query)
	results = list(cursor.fetchall()[0])
	results[2] = str(round(results[2]/10000000,2))+' Cr'
	results[-1] = str(results[-1])+' %'

	date_query = '''select max(date) from invoice_order where date <=
	'{}-03-31';'''.format(int(current_year)+1)
	cursor.execute(date_query)
	last_invoice_date = cursor.fetchall()[0][0].strftime("%d-%m-%Y")
	return render_template('index.html', results=results, last_invoice_date=last_invoice_date,
				year_list=global_data['year_list'], current_year=current_year)


@app.route("/<string:graph_name>.png", methods=['GET'])
def home_plot_graph(graph_name):
	cursor = db.cursor()
	current_year = graph_name[-4:]
	if graph_name[:-5] == 'cust_num':
		query = '''SELECT territory_name, num_customers FROM territory_profile 
		where time_bucket='{}' order by num_customers desc;
		'''.format(current_year)
		cursor.execute(query)
		results = cursor.fetchall()
		[x,y] = list(zip(*results))
		xlabel, ylabel = 'Territory', 'Customer number'
		title = 'Territory-wise Customer number'
		fig = create_bar_plot(x, y, xlabel, ylabel, title, # ylimit=(0, 25),\
							  width=0.5, rotation=30)

	elif graph_name[:-5] == 'sale':
		query = '''SELECT territory_name, sale_val FROM territory_profile 
		where time_bucket='{}' order by sale_val desc;
		'''.format(current_year)
		cursor.execute(query)
		results = cursor.fetchall()
		[x,y] = list(zip(*results))
		y = [round(a/10000000,2) for a in y]
		xlabel, ylabel = 'Territory', 'Sales (Crores)'
		title = 'Territory-wise sales in Crores'
		fig = create_bar_plot(x, y, xlabel, ylabel, title, # ylimit=(4, 13),\
							  width=0.5, rotation=30)

	elif graph_name[:-5] == 'avg_invoice_num': 
		query = '''SELECT territory_name, avg_num_invoice_per_month FROM territory_profile 
		where time_bucket='{}' order by avg_num_invoice_per_month desc;
		'''.format(current_year)
		cursor.execute(query)
		results = cursor.fetchall()
		[x,y] = list(zip(*results))
		xlabel, ylabel = 'Territory', 'Avg. number of invoices/month'
		title = 'Territory-wise avg. number of invoices/month'
		fig = create_bar_plot(x, y, xlabel, ylabel, title, # ylimit=(60, 110),\
							  width=0.5, rotation=30)

	elif graph_name[:-5] == 'avg_invoice_val': 
		query = '''SELECT territory_name, avg_invoice_val FROM territory_profile 
		where time_bucket='{}' order by avg_invoice_val desc;
		'''.format(current_year)
		cursor.execute(query)
		results = cursor.fetchall()
		[x,y] = list(zip(*results))
		xlabel, ylabel = 'Territory', 'Average invoice value'
		title = 'Territory-wise average invoice value'
		fig = create_bar_plot(x, y, xlabel, ylabel, title, # ylimit=(88000, 102500),\
							  width=0.5, rotation=30)

	elif graph_name[:-5] == 'skew_orderby_sale': 
		query = '''SELECT territory_name, percent_sale_subperiod_1, percent_sale_subperiod_2,
		percent_sale_subperiod_3, percent_sale_subperiod_4 FROM territory_profile 
		where time_bucket='{}' and time_bucket_type='year' order by sale_val desc;
		'''.format(current_year)
		cursor.execute(query)
		results = cursor.fetchall()
		[x, y1, y2, y3, y4] = list(zip(*results))
		xlabel, ylabel = 'Territory', 'Monthly skew pattern (average) (%)'
		title = 'Territory-wise monthly skew pattern in %'
		fig = create_multiple_bar_plot(x, y1, y2, y3, y4, xlabel, ylabel, title,\
							  width=0.5, rotation=30)

	elif graph_name[:-5] == 'skew_orderby_skew': 
		query = '''SELECT territory_name, percent_sale_subperiod_1, percent_sale_subperiod_2,
		percent_sale_subperiod_3, percent_sale_subperiod_4 FROM territory_profile 
		where time_bucket='{}' and time_bucket_type='year' order by percent_sale_subperiod_4 desc;
		'''.format(current_year)
		cursor.execute(query)
		results = cursor.fetchall()
		[x, y1, y2, y3, y4] = list(zip(*results))
		xlabel, ylabel = 'Territory', 'Monthly skew pattern (average) (%)'
		title = 'Territory-wise monthly skew pattern in %'
		fig = create_multiple_bar_plot(x, y1, y2, y3, y4, xlabel, ylabel, title,\
							  width=0.5, rotation=30)
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
	for year in global_data['year_list']:
		results[year] = {}
		for x,y in (month_list_results):
			if x[:4] == str(year):
				results[year][x[5:]] = round(y/10000000,2)

	x_dict, y_dict = {}, {}
	for year in global_data['year_list']:
		monthly_sales_dict = results[year]
		x,y = list(monthly_sales_dict.keys()),list(monthly_sales_dict.values())
		x = [int(a) for a in x]
		y = [a for _,a in sorted(zip(x,y))]
		x = ['APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', \
			'DEC', 'JAN', 'FEB', 'MAR']
		x = x[:len(y)]
		x_dict[year], y_dict[year] = x, y
	xlabel, ylabel = 'Month', 'Sales (Crores)'
	title = 'Month-wise plot (APR to MAR)'
	fig = create_multiple_line_plot(x_dict, y_dict, xlabel, ylabel,['bD--','rv--','go--'],\
						   global_data['year_list'], title, text_offset=0.3)
	fig.savefig(f'{upload_folder}/seasonality.png', dpi=100)

	return render_template('seasonality.html', \
							upload_folder=upload_folder)

	
@app.route("/customer_orders", methods=['GET', 'POST'])
def customer_orders():
	# results = {}
	territory_list=global_data['territory_list']
	# territory_list.append('Overall')
	cursor = db.cursor()
	selected_year = global_data['year_list'][-1]
	selected_plot = 'Scatter-plot'
	selected_territory = 'Overall'

	query = '''select customer_name, avg_invoice_val, avg_num_invoice_per_month 
	from customer_profile where time_bucket='{}';
	'''.format(selected_year)

	cursor.execute(query)
	results = cursor.fetchall()
	[cust_list, avg_order_val_list, avg_num_order_list] = list(zip(*results))
	xlabel, ylabel = 'Average order value', 'Average order number/month'
	title = f'Scatter plot for customer orders in {selected_year} (Overall)'
	fig = create_scatter_plot(avg_order_val_list, avg_num_order_list, 100, xlabel, ylabel, title)

	if request.method=='POST':
		# print(request.form)
		selected_year = request.form['year']
		selected_plot = request.form['plot']
		selected_territory = request.form['territory']

		if selected_plot == 'Scatter-plot':
			if selected_territory == 'Overall':
				query = '''select customer_name, avg_invoice_val, avg_num_invoice_per_month 
				from customer_profile where time_bucket='{}';
				'''.format(selected_year)
			else:
				query = '''select customer_name, avg_invoice_val, avg_num_invoice_per_month 
				from customer_profile where time_bucket='{}' and territory_name='{}';
				'''.format(selected_year, selected_territory)

			cursor.execute(query)
			results = cursor.fetchall()
			[cust_list, avg_order_val_list, avg_num_order_list] = list(zip(*results))
			xlabel, ylabel = 'Average order value', 'Average order number/month'
			title = f'Scatter plot for customer orders in {selected_year} ({selected_territory})'
			fig = create_scatter_plot(avg_order_val_list, avg_num_order_list, 100, xlabel, ylabel, title)
		
		elif selected_plot == 'Histogram':
			if selected_territory == 'Overall':
				query = '''select avg_num_invoice_per_month from customer_profile where 
				time_bucket='{}';'''.format(selected_year)
			else:
				query = '''select avg_num_invoice_per_month from customer_profile where 
				time_bucket='{}' and territory_name='{}';'''.format(selected_year, selected_territory)
			cursor.execute(query)
			results = list(zip(*cursor.fetchall()))[0]
			num_bins = 80
			xlabel, ylabel = 'Average order number/month', 'Number of occurances'
			title = f'Histogram of monthly customer orders in {selected_year}'
			fig = create_histogram(results, num_bins, xlabel, ylabel, title)

		elif selected_plot == 'Histogram (Total Sale)':
			if selected_territory == 'Overall':
				query = '''SELECT sum(sale_val) as total_sale FROM customer_profile 
				where time_bucket='{}' GROUP BY customer_name;'''.format(selected_year)
			else:
				query = '''SELECT sum(sale_val) as total_sale FROM customer_profile 
				where time_bucket='{}' and territory_name='{}' GROUP BY customer_name;
				'''.format(selected_year, selected_territory)
			cursor.execute(query)
			results = list(zip(*cursor.fetchall()))[0]
			results = [round(x/10000000,2) for x in results]
			num_bins = 50
			xlabel, ylabel = 'Total sale', 'Number of occurances'
			title = f'Histogram of customer sale in {selected_year}'
			fig = create_histogram(results, num_bins, xlabel, ylabel, title)
	
	fig.savefig(f'{upload_folder}/customer_orders_{selected_plot}_{selected_territory}_{selected_year}.png', \
				dpi=100)
	
	return render_template('customer_orders.html', \
							year_list=global_data['year_list'], \
							territory_list=territory_list,\
							upload_folder=upload_folder,\
							selected_year=selected_year,
							selected_plot=selected_plot, 
							selected_territory=selected_territory)


@app.route("/territory_wise_orders", methods=['GET', 'POST'])
def territory_wise_orders():
	results = {}
	cursor = db.cursor()
	selected_year = global_data['year_list'][-1]
	selected_territory = sorted(global_data['territory_list'])[0]
	query = '''select time_bucket, round(sale_val/avg_invoice_val) from territory_profile 
	where time_bucket_type='month' and territory_name='{}' order by time_bucket;
	'''.format(selected_territory)
	cursor.execute(query)
	month_list_results = cursor.fetchall()

	if request.method=='POST':
		selected_year = request.form['year']
		selected_territory = request.form['territory']
		query = '''select time_bucket, round(sale_val/avg_invoice_val) from territory_profile 
		where time_bucket_type='month' and territory_name='{}' order by time_bucket;
		'''.format(selected_territory)
		cursor.execute(query)
		month_list_results = cursor.fetchall()

	for m,n in (month_list_results):
		if m[:4] == str(selected_year):
			results[m[5:]] = n
	x,y = list(results.keys()),list(results.values())
	x = [int(a) for a in x]
	y = [a for _,a in sorted(zip(x,y))]
	y = [int(a) for a in y]
	x = ['APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', \
		'DEC', 'JAN', 'FEB', 'MAR']
	for i in range(12-len(y)):
		y.append(0)
	xlabel, ylabel = 'Month', 'Number of orders'
	title = f'Month-wise plot of number of orders for {selected_territory} in {selected_year} (APR to MAR)'
	fig = create_bar_plot(x, y, xlabel, ylabel, title, ylimit=(0, max(y)*1.5),\
							  width=0.5, rotation=30)
	fig.savefig(f'{upload_folder}/territory_wise_orders_{selected_territory}_{selected_year}.png', dpi=100)

	return render_template('territory_wise_orders.html', \
							year_list=global_data['year_list'], \
							territory_list=sorted(global_data['territory_list']),\
							upload_folder=upload_folder,\
							selected_year=selected_year,\
							selected_territory=selected_territory)


@app.route("/customer_coverage", methods=['GET', 'POST'])
def customer_coverage():
	results = {}
	total_num_customers = len(global_data['customer_list'])
	# terriotry_customer_dict = {}
	# for t in global_data['territory_list']:

	cursor = db.cursor()
	selected_year = global_data['year_list'][-1]
	selected_territory = 'Overall'
	query = '''select time_bucket, round(num_customers/{}, 2) from company_profile 
	where time_bucket_type='month' order by time_bucket;
	'''.format(total_num_customers)
	cursor.execute(query)
	month_list_results = cursor.fetchall()

	if request.method=='POST':
		selected_year = request.form['year']
		selected_territory = request.form['territory']
		
		if selected_territory == 'Overall':
			query1 = '''select time_bucket, round(num_customers/{}, 2) from company_profile 
			where time_bucket_type='month' order by time_bucket;
			'''.format(total_num_customers)
		else:
			query = '''select num_customers from territory_profile where territory_name='{}' 
			and time_bucket_type='year';
			'''.format(selected_territory)
			cursor.execute(query)
			selected_territory_num_cust = cursor.fetchall()[0][0]

			query1 = '''select time_bucket, round(num_customers/{},2) from territory_profile 
			where time_bucket_type='month' and territory_name='{}' order by time_bucket;
			'''.format(selected_territory_num_cust, selected_territory)

		cursor.execute(query1)
		month_list_results = cursor.fetchall()

	for m,n in (month_list_results):
		if m[:4] == str(selected_year):
			results[m[5:]] = n
	x,y = list(results.keys()),list(results.values())
	
	x = [int(a) for a in x]
	y = [float(a) for a in y]

	y = [a for _,a in sorted(zip(x,y))]
	x = ['APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', \
		'DEC', 'JAN', 'FEB', 'MAR']
	for i in range(12-len(y)):
		y.append(0.0)
	xlabel, ylabel = 'Month', 'Number of orders'
	title = f'Month-wise {selected_territory} customer coverage in {selected_year} (APR to MAR)'
	
	fig = create_bar_plot(x, y, xlabel, ylabel, title, ylimit=(0, max(y)*1.5),\
							  width=0.5, rotation=30)
	fig.savefig(f'{upload_folder}/customer_coverage_{selected_territory}_{selected_year}.png', dpi=100)

	return render_template('customer_coverage.html', \
							year_list=global_data['year_list'], \
							territory_list=sorted(global_data['territory_list']),\
							upload_folder=upload_folder,\
							selected_year=selected_year,\
							selected_territory=selected_territory)


@app.route("/sku_wise_orders", methods=['GET', 'POST'])
def sku_wise_orders():
	results = {}
	cursor = db.cursor()
	selected_year = global_data['year_list'][-1]
	selected_sku = sorted(global_data['sku_list'])[0]
	selected_territory = 'Overall'
	query = '''select time_bucket, round(sale_val/avg_invoice_val) from sku_profile 
	where time_bucket_type='month' and sku_name='{}' order by time_bucket;
	'''.format(selected_sku)
	cursor.execute(query)
	month_list_results = cursor.fetchall()

	if request.method=='POST':
		selected_year = request.form['year']
		selected_sku = request.form['sku']
		selected_territory = request.form['territory']
		if selected_territory == 'Overall':
			query = '''select time_bucket, round(sale_val/avg_invoice_val) from sku_profile 
			where time_bucket_type='month' and sku_name='{}' order by time_bucket;
			'''.format(selected_sku)
		else:
			query = '''select time_bucket, round(sale_val/avg_invoice_val) from 
			territory_sku_profile where time_bucket_type='month' and sku_name='{}' 
			and territory_name='{}' order by time_bucket;
			'''.format(selected_sku, selected_territory)
		cursor.execute(query)
		month_list_results = cursor.fetchall()

	for m,n in (month_list_results):
		if m[:4] == str(selected_year):
			results[m[5:]] = n
	x,y = list(results.keys()),list(results.values())
	x = [int(a) for a in x]
	y = [a for _,a in sorted(zip(x,y))]
	y = [int(a) for a in y]
	x = ['APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC','JAN','FEB','MAR']
	for i in range(12-len(y)):
		y.append(0)
	xlabel, ylabel = 'Month', 'Number of orders'
	title = f'Month-wise plot of number of orders for {selected_sku} in {selected_year} ({selected_territory})'
	fig = create_bar_plot(x, y, xlabel, ylabel, title, ylimit=(0, max(y)*1.5),\
							  width=0.5, rotation=30)
	fig.savefig(f'{upload_folder}/sku_wise_orders_{selected_sku}_{selected_territory}_{selected_year}.png', dpi=100)
		
	return render_template('sku_wise_orders.html', \
							year_list=global_data['year_list'], \
							sku_list=sorted(global_data['sku_list']),\
							territory_list=sorted(global_data['territory_list']),\
							upload_folder=upload_folder,\
							selected_year=selected_year,\
							selected_sku=selected_sku,
							selected_territory=selected_territory)

@app.route("/clustering", methods=['GET', 'POST'])
def clustering():
	customer_cluster_dict, customer_cluster_description_dict = \
										calc_cluster_of_entities(entity_type='customer')
	customer_cluster_list = list(customer_cluster_dict.keys())
	customer_cluster_avg_list = [customer_cluster_description_dict[x]['mean'] for x in customer_cluster_list]
	customer_cluster_list = [x for _,x in sorted(zip(customer_cluster_avg_list, customer_cluster_list))]

	sku_cluster_dict, sku_cluster_description_dict = calc_cluster_of_entities(entity_type='sku')
	sku_cluster_list = list(sku_cluster_dict.keys())
	sku_cluster_avg_list = [sku_cluster_description_dict[x]['mean'] for x in sku_cluster_list]
	sku_cluster_list = [x for _,x in sorted(zip(sku_cluster_avg_list, sku_cluster_list))]

	return render_template('clustering.html', \
							customer_cluster_list=customer_cluster_list, 
							customer_cluster_description=customer_cluster_description_dict,
							sku_cluster_list=sku_cluster_list, 
							sku_cluster_description=sku_cluster_description_dict)


@app.route("/top_contribution", methods=['GET', 'POST'])
def top_contribution():
	results = {
		'territory': {},
		'customer': {},
		'territory_wise_customer': {},
		'sku': {},
		'territory_wise_sku': {},
	}
	territory_wise_results = {}
	cursor = db.cursor()
	rank_dict = {
		'territory': list(range(1,4)),
		'customer': list(range(1,11)),
		'territory_wise_customer': list(range(1,4)),
		'sku': list(range(1,4)),
		'territory_wise_sku': list(range(1,4)),
	}
	for year in global_data['year_list']:
		query_overall = '''select sale_val from company_profile where 
		time_bucket='{}';'''.format(year)
		cursor.execute(query_overall)
		total_sale = cursor.fetchall()[0][0]
		query_territory = '''
		select territory_name, sale_val*100/{} from territory_profile where 
		time_bucket='{}' order by sale_val desc limit 3;'''.format(total_sale, year)
		cursor.execute(query_territory)
		results['territory'][year] = cursor.fetchall()

		query_customer = '''
		select customer_name, sale_val*100/{} from customer_profile where 
		time_bucket='{}' order by sale_val desc limit 10;'''.format(total_sale, year)
		cursor.execute(query_customer)
		results['customer'][year] = cursor.fetchall()

		query_sku = '''
		select sku_name, sale_val*100/{} from sku_profile where 
		time_bucket='{}' order by sale_val desc limit 3;'''.format(total_sale, year)
		cursor.execute(query_sku)
		results['sku'][year] = cursor.fetchall()

	top_territory_last_year = results['territory'][global_data['year_list'][-1]][0][0]

	for year in global_data['year_list']:
		selected_territory = top_territory_last_year
		query_total_sale_terr = '''select sale_val from territory_profile where 
		time_bucket='{}' and territory_name='{}';'''.format(year, selected_territory)
		cursor.execute(query_total_sale_terr)
		total_sale_terr = cursor.fetchall()[0][0]

		query_territory_wise_customer = '''select customer_name, sale_val*100/{} from 
		customer_profile where territory_name='{}' and time_bucket='{}' 
		order by sale_val desc limit 3;'''.format(total_sale_terr, selected_territory, year)
		cursor.execute(query_territory_wise_customer)
		results['territory_wise_customer'][year] = cursor.fetchall()

		selected_territory2 = top_territory_last_year

		query_territory_wise_sku = '''select sku_name, sale_val*100/{} from 
		territory_sku_profile where territory_name='{}' and time_bucket='{}' 
		order by sale_val desc limit 3;'''.format(total_sale_terr, selected_territory2, year)
		cursor.execute(query_territory_wise_sku)
		results['territory_wise_sku'][year] = cursor.fetchall()

	if request.method=='POST':
		for year in global_data['year_list']:
			try:
				selected_territory = request.form['territory']
				scroll = 'territorry_wise_customer'
			except:
				selected_territory = top_territory_last_year

			query_total_sale_terr = '''select sale_val from territory_profile where 
			time_bucket='{}' and territory_name='{}';'''.format(year, selected_territory)
			cursor.execute(query_total_sale_terr)
			total_sale_terr = cursor.fetchall()[0][0]

			query_territory_wise_customer = '''select customer_name, sale_val*100/{} from 
			customer_profile where territory_name='{}' and time_bucket='{}' 
			order by sale_val desc limit 3;'''.format(total_sale_terr,selected_territory, year)
			cursor.execute(query_territory_wise_customer)
			results['territory_wise_customer'][year] = cursor.fetchall()

			try:
				selected_territory2 = request.form['territory2']
				scroll = 'territorry_wise_sku'
			except:
				selected_territory2 = top_territory_last_year

			query_total_sale_terr = '''select sale_val from territory_profile where 
			time_bucket='{}' and territory_name='{}';'''.format(year, selected_territory2)
			cursor.execute(query_total_sale_terr)
			total_sale_terr2 = cursor.fetchall()[0][0]

			query_territory_wise_sku = '''select sku_name, sale_val*100/{} from 
			territory_sku_profile where territory_name='{}' and time_bucket='{}' 
			order by sale_val desc limit 3;'''.format(total_sale_terr2, selected_territory2, year)
			cursor.execute(query_territory_wise_sku)
			results['territory_wise_sku'][year] = cursor.fetchall()

		
		global_data['top_contribution'] = results
		return render_template('top_contribution.html', results=results,\
						year_list=global_data['year_list'],rank_dict=rank_dict,\
						territory_list=sorted(global_data['territory_list']), 
						selected_territory=selected_territory,
						selected_territory2=selected_territory2, scroll=scroll)
	
	global_data['top_contribution'] = results
	# print('results', results)
	return render_template('top_contribution.html', results=results,\
							year_list=global_data['year_list'],rank_dict=rank_dict,\
							territory_list=sorted(global_data['territory_list']), 
							selected_territory=selected_territory,
							selected_territory2=selected_territory2)


@app.route("/top_contribution/<string:graph_name>.png", methods=['GET'])
def top_contribution_plot_graph(graph_name):
	year = graph_name[:4]
	entity = graph_name[5:-2]
	rank = int(graph_name[-1])

	cursor = db.cursor()
	query = '''
	select num_customers, num_skus, num_territories from company_profile where time_bucket='{}'; 
	'''.format(year)
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
		fig = create_line_plot(x, y, xlabel, ylabel,'bD--',title)
			# ,text_offset=max(y)/40)
	elif rank == 0:
		# Overall analysis in pie chart
		[x,y] = zip(*global_data['top_contribution'][entity][year])
		x = list(x)
		y = [round(a,2) for a in y]
		others_percent = round(100-sum(y), 2)
		
		if entity == 'customer':
			x.append('Other {} customers'.format(entity_num[0]-10))
		elif entity == 'sku':
			x.append('Other {} skus'.format(entity_num[1]-3))
		elif entity == 'territory':
			x.append('Other {} territories'.format(entity_num[2]-3))
		y.append(others_percent)
		title = f'Pie-diagram for sales of {entity} in calender year-{year}'
		explode = [0.1]*(len(x)-1)
		explode.append(0)
		fig = create_pie_plot(x, y, explode, title)
	
	if len(request.args) == 1:
		cursor = db.cursor()
		terr_name = request.args['territory']

		if entity == 'customer':
			key_name = 'territory_wise_customer'
		elif entity == 'sku':
			key_name = 'territory_wise_sku'

		query = ''' 
		select num_customers, num_skus from territory_profile where time_bucket='{}'
		and territory_name='{}';'''.format(year, terr_name)
		cursor.execute(query)
		entity_num = cursor.fetchall()[0]


		# Overall analysis in pie chart
		[x,y] = zip(*global_data['top_contribution'][key_name][year])
		x = list(x)
		y = [round(a,2) for a in y]
		others_percent = round(100-sum(y), 2)

		if entity == 'customer':
			x.append('Other {} customers'.format(entity_num[0]-3))
		elif entity == 'sku':
			x.append('Other {} skus'.format(entity_num[1]-3))
		y.append(others_percent)
		title = f'Pie-diagram for sales of {entity} within territory {terr_name} in calender year-{year}'
		explode = [0.1]*(len(x)-1)
		explode.append(0)
		fig = create_pie_plot(x, y, explode, title)

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
	cagr_result['Overall'] = calculate_cagr(overall_df)

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

	x,y = list(cagr_result.keys()), list(cagr_result.values())
	overall_index = x.index('Overall')
	xlabel, ylabel = 'Territory', 'CAGR (%)'
	title = f'Territory-wise CAGR (%)'
	fig = create_bar_plot(x, y, xlabel, ylabel, title,
						width= 0.5, rotation=30, 
						specific_bar_index=overall_index)
	fig.savefig(f'{upload_folder}/cagr.png', dpi=100)

	return render_template('cagr.html', cagr_result=cagr_result, \
							upload_folder=upload_folder)


@app.route("/top_growing_sales", methods=['GET', 'POST'])
def top_growing_sales():
	results = {}
	results['territory'] = get_entity_wise_top_3_cagr('territory', reverse=True)
	results['customer'] = get_entity_wise_top_3_cagr('customer', reverse=True)
	results['sku'] = get_entity_wise_top_3_cagr('sku', reverse=True)

	rank_list = list(range(1,4))
	return render_template('top_growing_sales.html', results=results, rank_list=rank_list)


@app.route("/slowest_growing_sales", methods=['GET', 'POST'])
def top_declining_sales():
	results = {}
	results['territory'] = get_entity_wise_top_3_cagr('territory', reverse=False)
	results['customer'] = get_entity_wise_top_3_cagr('customer', reverse=False)
	results['sku'] = get_entity_wise_top_3_cagr('sku', reverse=False)

	rank_list = list(range(1,4))
	return render_template('slowest_growing_sales.html', results=results, rank_list=rank_list)


@app.route("/most_regular_invoices", methods=['GET', 'POST'])
def most_steady_sales():
	steady_sales_results = {}
	current_year = global_data['year_list'][-1]
	steady_sales_results['territory'] = get_entity_wise_most_3_steady_sales('territory')[current_year]
	steady_sales_results['customer'] = get_entity_wise_most_3_steady_sales('customer')[current_year]
	steady_sales_results['sku'] = get_entity_wise_most_3_steady_sales('sku')[current_year]
	if request.method=='POST':
		current_year = request.form['year']
		steady_sales_results['territory'] = get_entity_wise_most_3_steady_sales('territory')[current_year]
		steady_sales_results['customer'] = get_entity_wise_most_3_steady_sales('customer')[current_year]
		steady_sales_results['sku'] = get_entity_wise_most_3_steady_sales('sku')[current_year]
	
	rank_list = list(range(1,4))
	return render_template('most_regular_invoices.html', results=steady_sales_results, 
							year_list=global_data['year_list'], current_year=current_year,\
							rank_list=rank_list)


def get_entity_wise_top_3_cagr(entity_type, reverse=True):
	entity_dict = {}
	entity_query = '''
	select {}_name, time_bucket, sale_val from {}_profile where 
	time_bucket_type='month';'''.format(entity_type, entity_type)
	entity_df = pd.read_sql(entity_query, db)
	entity_list = entity_df[f'{entity_type}_name'].drop_duplicates(keep='first').tolist()
	for entity_name in entity_list:
		df = entity_df.loc[entity_df[f'{entity_type}_name']==entity_name,:]
		entity_dict[entity_name] = calculate_cagr(df)
	entity_dict_sorted = {k: v for k, v in sorted(entity_dict.items(), \
							key=lambda item: item[1], reverse=reverse)}
	return list(entity_dict_sorted.items())[:3]


def get_entity_wise_most_3_steady_sales(entity_type):
	entity_dict = {}
	for year in global_data['year_list']:
		entity_dict[year] = []
		entity_query = '''
		select {}_name, sd_num_invoice_per_month from {}_profile where 
		time_bucket='{}' order by sd_num_invoice_per_month limit 3;
		'''.format(entity_type, entity_type, year)
		entity_df = pd.read_sql(entity_query, db)
		entity_list = entity_df[f'{entity_type}_name'].drop_duplicates(keep='first').tolist()
		for entity_name in entity_list:
			sd_value = entity_df.loc[entity_df['{}_name'.format(entity_type)]==entity_name,\
									'sd_num_invoice_per_month'].values[0]
			entity_dict[year].append([entity_name, sd_value])
	return entity_dict


def calc_cluster_of_entities(entity_type='customer'):
	'''
	Necessary input:

	1. n_clusters: Required number of clusters
	2. entity_type: 'customer'/'sku'
	'''
	n_clusters_list = [2,3,4,5,6]
	query = '''
	SELECT {}_name, sum(sale_val) as total_sale FROM {}_profile 
	where time_bucket_type='year' GROUP BY {}_name;
	'''.format(entity_type, entity_type, entity_type)
	df = pd.read_sql(query, db)
	entity_sale_dict = df.set_index(f'{entity_type}_name')['total_sale'].to_dict()
	cluster_score_list = []
	for n_clusters in n_clusters_list:
		entity_cluster_dict, cluster_centre_dict = clustering_1D_kmeans(entity_sale_dict, \
								n_clusters=n_clusters, random_state=42)
		_, score = calculate_cluster_distance_and_score(entity_sale_dict,entity_cluster_dict, \
			cluster_centre_dict)
		cluster_score_list.append(score)

	kneedle = KneeLocator(n_clusters_list, cluster_score_list, S=1.0, \
						  curve='convex', direction='decreasing')
	opt_n_clusters = round(kneedle.knee)

	opt_entity_cluster_dict, _ = clustering_1D_kmeans(entity_sale_dict, \
								n_clusters=opt_n_clusters, random_state=42)
	opt_cluster_description_dict = describe_cluster(opt_entity_cluster_dict, \
									entity_sale_dict)
	return (opt_entity_cluster_dict, opt_cluster_description_dict)

if __name__ == '__main__':
	app.run(debug=True)