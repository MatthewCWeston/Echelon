import sqlparse
import itertools
from sqlparse.sql import IdentifierList, Identifier,Parenthesis, Token, Comparison, Where, Function
from sqlparse.tokens import Keyword, DML,Whitespace, Punctuation, Name
import re

# Tagging script by UIUC undergrad student Haorong Sun. Removes variable names.
TABLE = '_Table'
ALIAS = '_Alias'
COLUMN = '_Column'
NUM = '_Numeric_value'
STR = '_String'
COMMENT = '_Comment'
NAME = '_Name'
KEYWORDS = ['AS', 'COUNT']

def is_subquery(parsed):
	if not parsed.is_group:
		return False
	for item in parsed.tokens:
		if item.ttype is DML and item.value.upper() == 'SELECT':
			return True
	return False

def is_comment(i):
	if 'Token.Comment' in str(i.ttype):
		return True
	return False

def is_string(i):
	if 'Token.Literal.String' in str(i.ttype):
		return True
	return False

def is_number(i):
	if 'Token.Literal.Number' in str(i.ttype):
		return True
	return False

def is_name(i):
	if i.ttype is Name:
		return True
	return False


def break_comparison(where):
	if not where.is_group:
		return []
	return_list = []
	for i in where.tokens:
		if is_subquery(i):
				for x in get_column_identifier(i):
					return_list.append(x)
		elif isinstance(i, Identifier) or isinstance(i, Function):
			return_list.append(i)
		elif isinstance(i, Parenthesis) or isinstance(i, Comparison) or isinstance(i, Where):
			for x in break_comparison(i):
				return_list.append(x)
	return return_list

def get_value_token(parsed):
	result = []
	for item in list(parsed.tokens):
		
		if item.is_group:
			for x in get_value_token(item):
				result.append(x)
		elif is_string(item) or is_number(item) or is_comment(item):
			result.append(item)
			
	return result

def get_name_token(parsed):
	result = []
	for item in list(parsed.tokens):
		
		if item.is_group:
			for x in get_name_token(item):
				result.append(x)
		elif is_name(item) and item.value.upper() not in ['COUNT', 'MAX', 'MIN', 'AVG']:
			result.append(item)
			
	return result
	 

def get_table_identifier(parsed):
	from_flag = False
	view_flag = False
	result = []
	for item in list(parsed.tokens):
		if item.is_group:
			for x in get_table_identifier(item):
				result.append(x)
		if from_flag:
			if is_subquery(item):
				for x in get_table_identifier(item):
					result.append(x)
			elif item.ttype is Keyword and item.value.upper() in ['ORDER', 'GROUP', 'BY', 'HAVING', 'GROUP BY', 'ON', 'WHERE', 'SET']:
				from_flag = False
				break
			else:
				result.append(item)
		elif view_flag and not item.ttype == Whitespace:
			result.append(item)
			view_flag = False
		
		if (item.ttype is Keyword and item.value.upper()in ['FROM', 'INTO'] ) or ( item.ttype is DML and item.value.upper() == 'UPDATE' ):
			from_flag = True
		if item.ttype is Keyword and item.value.upper() == 'VIEW':
			view_flag = True
	return result


def get_column_identifier(parsed):
	select_flag = False
	on_flag = False
	result = []
	for item in list(parsed.tokens):
		if isinstance(item, Where) or isinstance(item, Comparison):
			for x in break_comparison(item):
				result.append(x)
		else:       
			if item.is_group:
				for x in get_column_identifier(item):
					result.append(x)
			if select_flag:
				if item.ttype is Keyword and item.value.upper() in ['ORDER', 'GROUP', 'BY', 'HAVING', 'GROUP BY', 'FROM', 'WHERE']:
					select_flag = False
				else:
					result.append(item) 
			elif on_flag:
				if item.ttype is Keyword and item.value.upper() in ['ORDER', 'GROUP', 'BY', 'HAVING', 'GROUP BY']:
					on_flag = False
				elif not item.ttype is Keyword:
					for x in break_comparison(item):
						result.append(x)
					
			if (item.ttype is DML and item.value.upper() == 'SELECT') or (item.ttype is Keyword and item.value.upper() == 'GROUP BY') :
				select_flag = True
			if item.ttype is Keyword and item.value.upper() in ['ON', 'HAVING']:
				on_flag = True
	return result



def decompose_identifiers(identifiers):
	result = []
	for item in identifiers:
		if isinstance(item, IdentifierList):
			for identifier in item.get_identifiers():               
				result.append(item)
		else:         
			result.append(item)
	return result



def helper_func(iden):
	table = None
	column = None
	if isinstance(iden, Identifier) and not isinstance(iden, Parenthesis):
		token_list = iden.tokens
		if len(token_list) < 3:
			return table,column

		if isinstance (token_list[0], Function):
			column = token_list[0]
		elif not token_list[0].is_group:
			table = token_list[0]
			column = token_list[2]
		else:
			table, column = helper_func(token_list[0])
			
		
	return table, column

def replace_text(line, key, value, column = 0):
	p_1 = [',', '.', ' ', '=', '>', '<', '\n', '(', ')', '/', '*', '+', '-', '!', '@']
	p_2 = [',', ' ', '=', '>', '<', '\n', '(', ')', ';', '/', '*', '+', '-', '!', ':']
	p_3 = [',', '.', ' ', '=', '>', '<', '\n', '(', ')', ';', '/', '*', '+', '-', '!']
	p_4 = [',', ' ', '=', '>', '<', '\n', '(', ')', ';', '/', '*', '+', '-', '%', '!']
	result = line
	if value == STR:
		result = result.replace(key, ' '+value+' ')
	
	elif column == 0: 
		for x in p_2:
			for y in p_1:
				result = result.replace(x + key + y , x + value + y)
	elif column == 1:
		for x in p_1:
			for y in p_2:
				result = result.replace(x + key + y , x + value + y)
	elif column == 2:
		if (len(key) > 1 and key[0] == '-'):
			key = key[1:]
		for x in p_4:
			for y in p_4:
				result = result.replace(x + key + y , x + value + y)
	else:
		for y in p_4:
			result = result.replace('.' + key + y , '.' + COLUMN + y)
			result = result.replace(y + key + '.' , y + TABLE + '.')
		for x in p_3:
			for y in p_3:
				result = result.replace(x + key + y , x + value + y)
	
	return result

def preprocess_query(sql, values, columns, alias, tables, names):
	for i in values:
		sql = replace_text(sql, i, values[i], 2)
	for i in alias:
		sql = replace_text(sql, i, alias[i])
	for i in columns:
		sql = replace_text(sql, i, columns[i], 1)
	for i in tables:
		sql = replace_text(sql, i, tables[i])
	for i in names:
		sql = replace_text(sql, i, names[i], 3)
		
	return sql

def is_punct(i):
	if 'Token.Text.Whitespace' in str(i.ttype) or i.ttype == Punctuation:
		return True
	return False

def extract_table(k, alias_map, column_map, table_map):
	if isinstance(k, Identifier) and k.has_alias():
		name = k.get_alias()
		if name not in KEYWORDS:
			alias_map[name] = ALIAS
		temp = k.tokens[0]
		tab,col = helper_func(temp)
		if not tab == None and tab.value not in alias_map:
			table_map[tab.value] = TABLE
		if not col == None and col.value.upper() not in KEYWORDS:
			column_map[col.value] = COLUMN
		if tab == None and col == None and temp.value.upper() not in KEYWORDS:
			table_map[temp.value] = TABLE
	elif not is_punct(k):
		tab,col = helper_func(k)
		if not tab == None and tab.value not in alias_map:
			table_map[tab.value] = TABLE
		if not col == None and col.value.upper() not in KEYWORDS:
			column_map[col.value] = COLUMN
		if (tab == None) and (col == None) and (k.value.upper() not in KEYWORDS):
			table_map[k.value] = TABLE
 
def extract_column(k, alias_map, column_map, table_map):
	if isinstance(k, Identifier) and k.has_alias():
		name = k.get_alias()
		if name not in KEYWORDS:
			alias_map[name] = ALIAS
		tab,col = helper_func(k)
		if not tab == None and tab.value not in alias_map:
			table_map[tab.value] = TABLE
		if not col == None and col.value.upper() not in KEYWORDS:
			column_map[col.value] = COLUMN
		if tab == None and col == None and k.value.upper() not in KEYWORDS:
			column_map[k.value] = COLUMN
	elif not is_punct(k): 
		tab,col = helper_func(k)
		if not tab == None and tab.value not in alias_map:
			table_map[tab.value] = TABLE
		if not col == None and col.value.upper() not in KEYWORDS:
			column_map[col.value] = COLUMN
		if (tab == None) and (col == None) and (k.value.upper() not in KEYWORDS):
			column_map[k.value] = COLUMN
				
				
def preprocess(sql_list):
	query_list = []
	
	for sql in sql_list:
		table_map = {}
		alias_map = {}
		column_map = {}
		value_map = {}
		name_map = {}
		columns = []
		tables = []
		values = []
		names = []
		sql += ' '
		statements = list(sqlparse.parse(sql))
		for statement in statements:
			values.append(set(get_value_token(statement)))
				
			names.append(set(get_name_token(statement)))
				
			stream = get_table_identifier(statement)
			tables.append(set(decompose_identifiers(stream)))

			stream = get_column_identifier(statement)
			columns.append(set(decompose_identifiers(stream)))
		
		for x in values:
			for i in x:
				if is_string(i):
					value_map[i.value] = STR
				elif is_number(i):
					value_map[i.value] = NUM
				elif is_comment(i):
					value_map[i.value] = COMMENT
					
		for x in names:
			for i in x:
				name_map[i.value] = NAME
		for x in tables:
			for i in x:
				if isinstance(i, Identifier) or isinstance(i, Function):
					extract_table(i, alias_map, column_map, table_map)
				elif isinstance(i, IdentifierList):
					for k in i.tokens:
						extract_table(k, alias_map, column_map, table_map)
					
		for x in columns:
			for i in x:
				if i.value in value_map:
					continue
				if isinstance(i, Identifier) or isinstance(i, Function):
					extract_column(i, alias_map, column_map, table_map)
				elif isinstance(i, IdentifierList):   
					for k in i.tokens:
						extract_column(k, alias_map, column_map, table_map)
						
		query_list.append(preprocess_query(sql, value_map, column_map, alias_map, table_map, name_map)) 
	return query_list

def processSubmission(content):
	content = content.replace( '%', ' % ')
	content = content.replace('#', '--')
	content = sqlparse.format(content,reindent=True, keyword_case='upper',strip_comments=True)
	content = preprocess([content])
	return content

# Conversion script by Matthew Weston. Converts tagged text to an input vector for the
# feature extractor.

vocab = {'SELECT': 0, '_ALIAS': 1, '.': 2, '_COLUMN': 3, ',': 4, 'COUNT': 5, '(': 6, ')': 7, 'FROM': 8, '_TABLE': 9, 'JOIN': 10, 'WHERE': 11, '>': 12, 'GROUP': 13, 'BY': 14, 'LEFT': 15, 'OUTER': 16, 'ON': 17, '=': 18, 'AS': 19, 'CREATE': 20, 'TABLE': 21, '*': 22, 'AND': 23, ';': 24, '_NUMERIC_VALUE': 25, 'IS': 26, 'NULL': 27, 'OR': 28, '<': 29, 'ORDER': 30, 'INNER': 31, '_NAME': 32, 'DISTINCT': 33, 'NUMBER': 34, 'DATE': 35, 'LIKE': 36, 'NOT': 37, 'IN': 38, '-': 39, 'NATURAL': 40, 'CURRENT': 41, 'CASE': 42, 'WHEN': 43, 'THEN': 44, 'END': 45, 'CROSS': 46, 'ANY': 47, '_STRING': 48, 'EXISTS': 49, 'HAVING': 50, 'OLD': 51, 'TEMP': 52, 'USING': 53, 'RIGHT': 54, 'ALL': 55, 'DESC': 56, 'VIEW': 57, '!': 58, 'NEW': 59, 'PRIOR': 60, 'ASC': 61, '&': 62, 'FINAL': 63, 'ELSE': 64, '/': 65, 'BETWEEN': 66, 'TEMPORARY': 67, 'UNION': 68, 'SET': 69, ':': 70, '+': 71, 'UPDATE': 72, 'INSERT': 73, 'INTO': 74, 'VALUES': 75, '@': 76, 'LIMIT': 77, 'MAX': 78, 'MIN': 79, '%': 80, 'CHAR': 81, 'MOD': 82, 'TRIGGER': 83, 'BEFORE': 84, 'FOR': 85, 'EACH': 86, 'ROW': 87, 'BEGIN': 88, 'DECLARE': 89, 'INT': 90, 'IF': 91, 'DEFAULT': 92, 'AFTER': 93, 'INTEGER': 94, 'DELETE': 95, 'AVG': 96, 'MERGE': 97, 'TRUE': 98, 'RESULT': 99, 'ALTER': 100, 'ADD': 101, 'INITIAL': 102, 'DROP': 103, 'SIGNAL': 104, 'SQLSTATE': 105, 'MESSAGE_TEXT': 106, 'TRIGGER_NAME': 107, 'FIRST': 108, 'SECOND': 109, 'MODIFY': 110, 'ROWS': 111}
def textToInput(txt):
	content = processSubmission(txt)[0]
	content = content.upper()
	content = re.findall('[\w\d]+|[^\w|\d|\s]', content)
	inputVector = []
	for word in content:
		if (word not in vocab):# Unhandled vocabulary. Either this isn't valid SQL or the vocabulary isn't complete.
			return False
		else:
			inputVector.append(vocab[word])
	return inputVector