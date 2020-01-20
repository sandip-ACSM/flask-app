import os
import io
import math
import json
from datetime import datetime
import pymysql
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

config = ConfigParser()
config.read('config.ini')

host  = config['database']['endpoint']
username = config['database']['username']
password = config['database']['password']
db_name = config['database']['db_name']

upload_folder = config['upload_folder']['location']


app = Flask(__name__)
global_data = {}
db = pymysql.connect(host, username, password, db_name)

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
	current_year = global_data['year_list'][-1]
	query = '''SELECT num_territories, num_customers, sale_val, 
		avg_num_invoice_per_month, avg_invoice_val, month_end_skew FROM 
		company_profile where time_bucket='{}';'''.format(current_year)
	cursor.execute(query)
	if request.method=='POST':
		current_year = request.form['year']
		query = '''SELECT num_territories, num_customers, sale_val, 
		avg_num_invoice_per_month, avg_invoice_val, month_end_skew FROM 
		company_profile where time_bucket='{}';'''.format(current_year)
		cursor.execute(query)
	results = list(cursor.fetchall()[0])
	results[2] = str(round(results[2]/10000000,2))+' Cr'
	results[-1] = str(results[-1])+' %'

	date_query = '''select max(date) from invoice_order where date<=
	'{}-12-31';'''.format(current_year)
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
		where time_bucket='{}' and time_bucket_type='year' order by num_customers desc;
		'''.format(current_year)
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

	elif graph_name[:-5] == 'sale':
		query = '''SELECT territory_name, sale_val FROM territory_profile 
		where time_bucket='{}' and time_bucket_type='year' order by sale_val desc;
		'''.format(current_year)
		cursor.execute(query)
		results = cursor.fetchall()
		[x,y] = list(zip(*results))
		y = [round(a/10000000,2) for a in y]
		xlabel, ylabel = 'Territory', 'Sales (Crores)'
		title = 'Territory-wise sales in Crores'
		fig = create_bar_plot(x, y, xlabel, ylabel, title,ylimit=(4, 13),\
							  width=0.5, rotation=30, text_offset=0.05)
		output = io.BytesIO()
		FigureCanvas(fig).print_png(output)
		return Response(output.getvalue(), mimetype='image/png')

	elif graph_name[:-5] == 'avg_invoice_num': 
		query = '''SELECT territory_name, avg_num_invoice_per_month FROM territory_profile 
		where time_bucket='{}' and time_bucket_type='year' order by avg_num_invoice_per_month desc;
		'''.format(current_year)
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


	elif graph_name[:-5] == 'avg_invoice_val': 
		query = '''SELECT territory_name, avg_invoice_val FROM territory_profile 
		where time_bucket='{}' and time_bucket_type='year' order by avg_invoice_val desc;
		'''.format(current_year)
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

	elif graph_name[:-5] == 'skew': 
		query = '''SELECT territory_name, month_end_skew FROM territory_profile 
		where time_bucket='{}' and time_bucket_type='year' order by month_end_skew desc;
		'''.format(current_year)
		cursor.execute(query)
		results = cursor.fetchall()
		[x,y] = list(zip(*results))
		xlabel, ylabel = 'Territory', 'Month end skew (%)'
		title = 'Territory-wise month end skew in %'
		fig = create_bar_plot(x, y, xlabel, ylabel, title,ylimit=(30, 46),\
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

	return render_template('seasonality.html', results=results,\
							year_list=global_data['year_list'], \
							upload_folder=upload_folder) 


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
		time_bucket='{}' order by sale_val desc limit 10;'''.format(total_sale, year)
		cursor.execute(query_customer)
		results['customer'][year] = cursor.fetchall()

		query_sku = '''
		select sku_name, sale_val*100/{} from sku_profile where 
		time_bucket='{}' order by sale_val desc limit 3;'''.format(total_sale, year)
		cursor.execute(query_sku)
		results['sku'][year] = cursor.fetchall()
		
	global_data['top_contribution'] = results
	# print(global_data['top_contribution'])
	rank_dict = {
		'territory': list(range(1,4)),
		'customer': list(range(1,11)),
		'sku': list(range(1,4))
	}
	return render_template('top_contribution.html', results=results,\
							year_list=global_data['year_list'],rank_dict=rank_dict)


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
	return render_template('cagr.html', cagr_result=cagr_result, 
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
def top_growing_sales():
	results = {}
	results['territory'] = get_entity_wise_top_3_cagr('territory', reverse=True)
	results['customer'] = get_entity_wise_top_3_cagr('customer', reverse=True)
	results['sku'] = get_entity_wise_top_3_cagr('sku', reverse=True)
	return render_template('top_growing_sales.html', results=results)


@app.route("/slowest_growing_sales", methods=['GET', 'POST'])
def top_declining_sales():
	results = {}
	results['territory'] = get_entity_wise_top_3_cagr('territory', reverse=False)
	results['customer'] = get_entity_wise_top_3_cagr('customer', reverse=False)
	results['sku'] = get_entity_wise_top_3_cagr('sku', reverse=False)
	return render_template('slowest_growing_sales.html', results=results)


@app.route("/most_steady_sales", methods=['GET', 'POST'])
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
	return render_template('most_steady_sales.html', results=steady_sales_results, 
							year_list=global_data['year_list'], current_year=current_year)


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
	plt.yticks(fontsize=15)
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


def create_multiple_line_plot(x_dict, y_dict, xlabel, ylabel, linetype_list, label_list, \
							  title, xlimit=(), ylimit=(), rotation=0, text_offset=0):
	'''
	This function draws multiple line graphs on a single plot. The data is given
	in form of a dict as follows:

	x_dict = {
		'label1': [...],
		'label2': [...],
		...
	}
	y_dict = {
		'label1': [...],
		'label2': [...],
		...
	}
	'''
	fig = plt.figure(figsize=(12,8), dpi=100)
	ax = fig.add_subplot(111)
	for ind, (label, linetype) in enumerate(zip(label_list, linetype_list)):
		x, y = x_dict[label], y_dict[label]
		plt.plot(range(len(x)), y, linetype, label=label, linewidth = 1.5)
		if ind == 0:
			plt.xticks(range(len(x)), x, fontsize=14, rotation=rotation)
		for i, j in enumerate(y):
			ax.text(i, j+text_offset, j, fontsize=15, ha='center',color = linetype[0])
	plt.xlabel(xlabel, fontsize=14)
	plt.ylabel(ylabel, fontsize=14)
	plt.title(title, fontsize=15)
	plt.grid(linestyle = '--', linewidth = 0.2, color = 'k')
	plt.yticks(fontsize=14)
	plt.legend(loc='best', fontsize=14)
	
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


if __name__ == '__main__':
	app.run(debug=True)