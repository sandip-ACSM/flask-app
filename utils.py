import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from statistics import mean, pstdev

def create_bar_plot(label_list, y, xlabel, ylabel, title, ylimit=(),\
					width=0.8, rotation=0, bottom=0,text_offset=0,\
					specific_bar_index=-1, specific_bar_color='r'):
	min_y, max_y = min(y), max(y)
	y_int = max_y-min_y
	if text_offset == 0:
		text_offset = y_int/30

	fig = plt.figure(figsize=(12,8), dpi=100)
	ax = fig.add_subplot(111)
	xrange = list(range(len(label_list)))
	barlist = plt.bar(xrange, y, width=width, align='center')
	if specific_bar_index != -1:
		barlist[specific_bar_index].set_color('r')
	plt.xticks(xrange, label_list, fontsize=14, rotation=rotation)
	plt.yticks(fontsize=14)
	plt.xlabel(xlabel, fontsize=14)
	plt.ylabel(ylabel, fontsize=14)
	plt.title(title, fontsize=15)
	plt.grid(linestyle = '--', linewidth = 0.15, color = 'k')
	if len(ylimit) !=0:
		plt.ylim(ylimit[0], ylimit[1])
	else:
		plt.ylim(min_y-0.3*y_int, max_y+0.3*y_int)
	for i, j in enumerate(y):
		if j != 0:
			ax.text(i, j+text_offset, j, fontsize=15, ha='center')
	plt.tight_layout()
	ax.spines['top'].set_visible(False)
	ax.spines['right'].set_visible(False)
	# ax.spines['bottom'].set_visible(False)
	ax.spines['left'].set_visible(False)
	return fig

def create_multiple_bar_plot(labels, y1, y2, y3, y4, xlabel, ylabel, title, \
					width=0.5, rotation=0, text_offset=0):
	fig = plt.figure(figsize=(12,8), dpi=100)
	ax = fig.add_subplot(111)
	def autolabel(rects):
		for rect in rects:
			height = rect.get_height()
			ax.annotate('{}'.format(height),
						xy=(rect.get_x() + rect.get_width() / 2, height),
						xytext=(0, text_offset), 
						textcoords="offset points",
						ha='center', va='bottom')

	x = np.array([3*a for a in range(len(labels))]) # the label locations

	rects1 = ax.bar(x - 3*width/2, y1, width,alpha=0.75, label='Subperiod-1')
	autolabel(rects1)
	rects2 = ax.bar(x - width/2, y2, width,alpha=0.75, label='Subperiod-2')
	autolabel(rects2)
	rects3 = ax.bar(x + width/2, y3, width,alpha=0.75, label='Subperiod-3')
	autolabel(rects3)
	rects4 = ax.bar(x + 3*width/2, y4, width,alpha=0.75, label='Subperiod-4')
	autolabel(rects4)

	plt.yticks(fontsize=14)
	ax.set_ylabel(ylabel, fontsize=14)
	ax.set_title(title, fontsize=14)
	ax.set_xticks(x)
	ax.set_xticklabels(labels, rotation=rotation, fontsize=14)
	ax.legend(loc=0,fontsize=12)
	plt.grid(linestyle = '--',linewidth = 0.2,color='k')

	fig.tight_layout()
	ax.spines['top'].set_visible(False)
	ax.spines['right'].set_visible(False)
	# ax.spines['bottom'].set_visible(False)
	ax.spines['left'].set_visible(False)
	return fig


def create_line_plot(x, y, xlabel, ylabel, linetype, title,
					 xlimit=(), ylimit=(), rotation=0, text_offset=0):
	min_y, max_y = min(y), max(y)
	y_int = max_y-min_y
	if text_offset == 0:
		text_offset = y_int/30

	fig = plt.figure(figsize=(12,8), dpi=100)
	ax = fig.add_subplot(111)
	plt.plot(range(len(x)), y, linetype, linewidth = 1.5)
	plt.xlabel(xlabel, fontsize=14)
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
	else:
		plt.ylim(min_y-0.3*y_int, max_y+0.3*y_int)
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
	# colors=['dodgerblue', 'yellowgreen', 'plum', 'tomato']
	ax.pie(y, explode=explode, labels=x, autopct='%1.2f%%', #colors=colors,
		shadow=True, startangle=0, textprops={'size': 'x-large'})
	ax.axis('equal')
	plt.title(title, fontsize=17)
	return fig


def create_histogram(x, num_bins, xlabel, ylabel, title):
	fig = plt.figure(figsize=(8,8), dpi=100)
	ax = fig.add_subplot(111)
	# num_bins = 75
	n, bins, patches = plt.hist(x, num_bins, facecolor='blue', \
								alpha=0.65)
	plt.xlabel(xlabel, fontsize=14)
	plt.ylabel(ylabel, fontsize=14)
	plt.title(title, fontsize=16)
	plt.grid(linestyle='--', linewidth=0.2, color='k')
	plt.xticks(fontsize=14)
	plt.yticks(fontsize=14)
	plt.tight_layout()
	ax.spines['top'].set_visible(False)
	ax.spines['right'].set_visible(False)
	# ax.spines['bottom'].set_visible(False)
	ax.spines['left'].set_visible(False)
	return fig

def create_scatter_plot(x, y, size, xlabel, ylabel, title):
	fig = plt.figure(figsize=(8,8), dpi=100)
	ax = fig.add_subplot(111)    
	plt.scatter(x, y, size, c="b", alpha=0.6, #marker=r'$\clubsuit$',
				label="Luck", edgecolors='k', linewidths=2)
	plt.xlabel(xlabel, fontsize=14)
	plt.ylabel(ylabel, fontsize=14)
	plt.title(title, fontsize=15)
	# plt.legend(loc='best')
	plt.grid(linestyle='--', linewidth=0.2, color='k')
	plt.xticks(fontsize=14)
	plt.yticks(fontsize=14)
	fig.tight_layout()
	# ax.spines['top'].set_visible(False)
	# ax.spines['right'].set_visible(False)
	# ax.spines['bottom'].set_visible(False)
	# ax.spines['left'].set_visible(False)
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


def clustering_1D_kmeans(input_dict, n_clusters, random_state):
	'''
	This function creates clusters of input data with one variable. The return value
	is a dictionary with cluster numbers 0,1,2, ... as keys.

	Input parameters:

	1. input_dict: A dict containing the input data with format:
			input_dict = {
				'entity_1': 23,
				'entity_2': 32,
				...
			}
	2. n_clusters: Number of required clusters
	3. random_state: A random state value required for kmeans clustering.
	'''
	intput_values = [[x] for x in input_dict.values()]
	X = np.array(intput_values)
	kmeans = KMeans(n_clusters=n_clusters, random_state=random_state).fit(X)
	cluster_dict = {}
	for i,j in zip(list(input_dict.keys()), kmeans.labels_):
		try:
			cluster_dict['Cluster_'+str(j)].append(i)
		except:
			cluster_dict['Cluster_'+str(j)] = [i]
	return cluster_dict

def describe_cluster(cluster_dict, input_dict):
	'''
	This function returns the upperlimit, lower limit, mean and standard deviation
	results for each cluster in form of a dict:

	result_dict = {
		'cluster_1': {
			'num': ...,
			'upper_limit': ...,
			'lower_limit': ...,
			'mean': ...,
			'sd': ...
		},
		'cluster_2': {
			.num': ...,
			'upper_limit': ...,
			'lower_limit': ...,
			'mean': ...,
			'sd': ...
		},
		...
	}
	'''
	result_dict = {}
	for key in cluster_dict.keys():
		result_dict[key] = {}
		tmp_list = [input_dict[x] for x in cluster_dict[key]]
		result_dict[key]['num'] = len(tmp_list)
		result_dict[key]['upper_limit'] = round(max(tmp_list),2)
		result_dict[key]['lower_limit'] = round(min(tmp_list),2)
		result_dict[key]['mean'] = round(mean(tmp_list),2)
		result_dict[key]['sd'] = round(pstdev(tmp_list),2)
	return result_dict
