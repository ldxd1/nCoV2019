#Read in individual cases of nCov2019 from https://docs.google.com/spreadsheets/d/1itaohdPiAeniCXNlntNztZ_oRvjh0HsGuJXUJWET008/edit?usp=sharing
# (url set by config.gspread_url)

from feather import read_dataframe, write_dataframe
from functions_clean import *

import pandas as pd
import matplotlib.pyplot as plt

pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 1000)
pd.options.mode.use_inf_as_na = True

# Read df.feather from gspread_url (see data_download.py)
df = read_dataframe('data/df_raw.feather')
#combined_dat = read_dataframe('data/combined_dat.feather')

# get column data types
print(df.dtypes)

col_date = list(filter(lambda x:'date' in x, df.columns))
col_date.remove("travel_history_dates")
col_admin = list(filter(lambda x:'admin' in x, df.columns))
col_float = ['age','latitude','longitude']
col_bin = ['wuhan(0)_not_wuhan(1)','chronic_disease_binary']   #sex',
col_cat = ['city','province','country','geo_resolution','location','lives_in_Wuhan',
           'outcome','reported_market_exposure','sequence_available']    #drop 'country_new'
col_str = col_admin + ['ID','chronic_disease','symptoms',
            'travel_history_location','source',
            'notes_for_discussion','additional_information']


####### DATES #############
# Clean dates
# Only date_confirmation can be filled in with an estimate of ~01-01-2020 at this point
df['date_confirmation'] = df['date_confirmation'].apply(clean_date, missing='01-01-2020', validStart='01-08-2019')
df.date_confirmation.value_counts(dropna=False).sort_index()

# The other dates should be left None if missing
for c in ['date_onset_symptoms', 'date_admission_hospital', 'date_death_or_discharge']:
    #print(df[c].value_counts(dropna=False).sort_index())
    df[c] = df[c].apply(clean_date, missing='', validStart='01-08-2019')
    print(df[c].value_counts(dropna=False).sort_index())

###### NUMERIC ###########
# Clean numeric values and plot histograms
# Clean age
df.age.value_counts(dropna=False)
df.age = df.age.apply(clean_age)
df.age.value_counts(dropna=False)
df.age.hist(bins=100)
plt.show()   #mean approx 50 yrs

# Clean latitudes, longitudes
for c in ['latitude','longitude']:
    df[c] = df[c].apply(clean_float)
    print(df[c].value_counts(dropna=False).sort_index())
    df[c].hist(bins=100)
    plt.show()


###### BINARY, CATEGORICAL ###########
# Get freq counts for col_bin
for c in col_bin:
    print("Before cleaning:")
    print(df[c].value_counts())
    df[c] = df[c].apply(clean_bin, missing=0)
    print("After cleaning:")
    print(df[c].value_counts(dropna=False).sort_index())
#    df[c].hist(bins=100)
#    plt.show()

# Before  cleaning
for c in col_cat:
    print(df[c].value_counts(dropna=False).sort_index())

# Recode into fewer, more meaningful categories
df.sequence_available = recode(df.sequence_available,
                                { "yes": 1}
                                , inplace=False, missing=0)

df.reported_market_exposure = recode(df.reported_market_exposure,
                                    {   "yes": 1,
                                        "no": 0,
                                        "yes, retailer in the seafood wholesale market": 1,
                                        "working in another market in Wuhan" : 1,
                                        '18.01.2020 - 23.01.2020': 1,
                                        '18.01.2020 - 23.01.2019': 1}
                        , inplace=False, missing=None)

df.outcome = recode(df.outcome,
                    { "died": 'died',
                     "discharged": 'discharged',
                     'stable':'ongoing',
                     'Symptoms only improved with cough. Currently hospitalized for follow-up.': 'ongoing'}
                    , inplace=False, missing='ongoing')

#After cleaning
for c in col_cat:
    print(df[c].value_counts(dropna=False).sort_index())


# Recode to new variables
df['wuhan'] = 1-df['wuhan(0)_not_wuhan(1)'].astype('int')
df.drop(columns='wuhan(0)_not_wuhan(1)')
df['died'] = recode(df.outcome,
                    { "died": 1}
                    , inplace=False, missing = 0).astype('int')
df['male'] = recode(df.sex, {"female": 0, "male": 1}, inplace=False, missing=np.nan).astype('float')
df['china'] = recode(df.country, {"China": 1}, inplace=False, missing=0).astype('int')

# Check for missingness and whether appropriate as features
df.age.value_counts(dropna=False)    #95% missing
df.male.value_counts(dropna=False)   #95% missing
df.wuhan.value_counts(dropna=False)
df.china.value_counts(dropna=False)
df.chronic_disease_binary.value_counts(dropna=False)
df.died.value_counts(dropna=False)   #0.3%

# mortality rate
df['died'].sum()/df.shape[0]*100



# Calculate features from dates
print(col_date)
df['days_onset_outcome'] = (df['date_death_or_discharge'] - df['date_onset_symptoms']).astype('timedelta64[D]')
df['days_onset_confirm'] = (df['date_confirmation'] - df['date_onset_symptoms']).astype('timedelta64[D]')
df['days_hosp'] = (df['date_death_or_discharge'] - df['date_admission_hospital']).astype('timedelta64[D]')
df['days_admin_confirm'] = (df['date_confirmation'] - df['date_admission_hospital']).astype('timedelta64[D]')

col_days = list(filter(lambda x:'days' in x, df.columns))
for c in col_days:
    df[c].plot.hist(bins=50, title=c)
    plt.show()

# write cleaned up  df
df.dtypes
write_dataframe(df, 'data/df.feather')

# construct subset with complete rows
df[df.age.notna()]['male'].value_counts(dropna=False)
df[df.male.notna()]['age'].value_counts(dropna=False)
df_complete_subset = df[(df.age.notna()) & (df.male.notna())]
print(df_complete_subset.shape)      #766 rows
df_complete_subset.age.value_counts(dropna=False).sort_index()
df_complete_subset.male.value_counts(dropna=False).sort_index()

write_dataframe(df_complete_subset, 'data/df_complete_subset.feather')

#impute missing values
df.age.median()   #48 yrs old
df_imputed = df
df_imputed.age = df.age.fillna(50,inplace=False)

write_dataframe(df_imputed, 'data/df_imputed.feather')