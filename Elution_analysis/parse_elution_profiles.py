#USAGE: Takes the processed results of an LC/MC2 experiment (.csv) and adds new columns with information about the protein and each peptide from a matching FASTA file.

#NOTE: This code will only run with Pandas 0.18 or higher (str.split function)
#NOTE: To compute total count, groupby rows where Appearance==1 or peptides that show up more than once in a protein will overincrease the total Count value



import sys 
#importing local updated Pandas module
sys.path.append("/home/nag2378/.local/lib/python2.7/site-packages")
import pandas as pd
from Bio import SeqIO
from regex import search,findall,finditer
from pandas import Series,DataFrame
from Bio.SeqRecord import SeqRecord
from Bio.Seq import Seq 
import argparse


def pep_start(row):
        #correct leucine-isoleucine insensibility
        pep = row['Peptide'].replace('I','J').replace('L','J').replace('J','(I|L)')
        seq = row['Sequence']
        #if it matches more than once, return a list of positions
        if len(findall(pep,seq)) > 1:
                runs = finditer(pep,seq)
                coord = []
		string = ''
		firstart = True
                for match in runs:
			if firstart:
				string = str(match.start()+1)
				firstart = False
			else:	string+= ','+str(match.start()+1)
                return string
        elif len(findall(pep,seq)) == 1:
                return str(search(pep,seq).start())
        else: return 'Not found'

#idem last function, end position
def pep_end(row):
        #correct leucine-isoleucine insensibility
        pep = row['Peptide'].replace('I','J').replace('L','J').replace('J','(I|L)')
        seq = row['Sequence']
        #if it matches more than once, return a list of positions
        if len(findall(pep,seq)) > 1:
                runs = finditer(pep,seq)
		string = ''
		firstend = True
                for match in runs:
			if firstend:
				string = str(match.end())
				firstend = False
			else:	
				string+= ','+str(match.end())
                return string
        elif len(findall(pep,seq)) == 1:
                return str(search(pep,seq).end())
        else: return 'Not found'


def add_columns(fasta, exp_data, output_file):
	proteome = list(SeqIO.parse(fasta,"fasta"))

	#import experimental results from LC/MS
	#data = pd.read_csv(exp_data,sep=',',header=0,names=['ProteinID','Peptide','Fraction','Count'])	
        #Possible columns headers: ProteinID,Peptide,FractionID,PeptideCount,PeptideArea,Label
	data = pd.read_csv(exp_data,usecols=['ProteinID','Peptide','FractionID','PeptideCount', 'PeptideArea', 'ExperimentID'])
	#data = data[['ProteinID','Peptide','FractionID','PeptideCount',']
	#data.columns = ['ProteinID','Peptide','Fraction','Count']
	data =  data.dropna().set_index('ProteinID')
	
	
	#create a list with the IDs and sequences of the proteins in the given proteome
	
	list_seq = []
	for protein in proteome:
	        list_seq.append([str(protein.id),str(protein.seq)])
	
	#turn that list into a dataframe
	sequences = DataFrame(list_seq,columns=['ProteinID','Sequence']).set_index('ProteinID')
	
	#append sequences to the original dataframe
	tmp = data.join(sequences)
	
	#return starting position of peptide with respect to the protein on the same row
	#add the three columns using the functions previously defined
	tmp['Start'] =  tmp.apply(pep_start,axis=1)
	tmp['End'] = tmp.apply(pep_end,axis=1)
	tmp['Length'] = tmp['Sequence'].map(len)
	tmp = tmp.reset_index()

	#split multiple start sites
	multistart = tmp['Start'].str.split(',', expand=True).stack()
	multistart.index = multistart.index.droplevel(-1)
	multistart.name = 'Start'
	
	#split multiple end sites
	multiend = tmp['End'].str.split(',', expand=True).stack()
	multiend.index = multiend.index.droplevel(-1)
	multiend.name = 'End'
	tmp.drop(['Start', 'End'], inplace=True, axis=1)
	
	#add new sites to original dataframe
	multiboth = pd.DataFrame({'Start':multistart, 'End':multiend}, index=multistart.index)
	final = tmp.join(multiboth)
	#reorder columns
	final = final[['ProteinID','Peptide','FractionID','PeptideCount','Sequence','Length','Start','End', 'ExperimentID', 'PeptideArea']]
	
	#reindex to add Appearance
	final = final.set_index(['ProteinID','Peptide','FractionID'])
	#add 'Appearance' column for peptides that appear multiple times
	final['Appearance'] = final.groupby(final.index).cumcount() + 1 
	#reindex to original index
	final = final.reset_index().set_index(['ProteinID','Peptide'])
	
	#test peptide with multiple appearances
        #ONLY test for arabidopsis data
	#print final.ix['sp|Q9FKA5|Y5957_ARATH'].ix['KPSYGR']
	
	final.to_csv(output_file)


def parse_args():
	parser = argparse.ArgumentParser(description = 'Takes the processed results of an LC/MC2 experiment (.csv) and adds new columns with information about the protein and each peptide from a matching FASTA file.')
	parser.add_argument('fasta', type = str, help = 'FASTA file containing entries for all the identified proteins of an LC/MC2 experiment.')
	parser.add_argument('exp_data', type = str, help = 'Results of an LC/MC2 experiment (.csv). There should be four headed columns: Protein, Peptide, Fraction, Count.')
	parser.add_argument('output_file',type = str, help = 'Name of the output file where the new table will be saved.')
	return parser.parse_args()	

def main():
	args = parse_args()
	add_columns(args.fasta, args.exp_data, args.output_file)
	print "All done! Output file: "+args.output_file


if __name__ == '__main__':
	main()
