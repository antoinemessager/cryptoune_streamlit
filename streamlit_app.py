import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import datetime

min_date=st.selectbox('Select period',['1 week','6h','12h','1 day','2 days','2 weeks','1 month','all'])
d={'6h':6,'12h':12,'1 day':24,'2 days':48,'1 week':7*24,'2 weeks':14*24,'1 month':30*24,'all':int(1e6)}
nb_hours=d[min_date]
st.session_state.nb_hours=min_date
if 'nb_hours' in st.session_state:
   #loading info
   df_monitoring=pd.read_excel('https://docs.google.com/spreadsheets/d/e/2PACX-1vSTqIh7BXEaPKj1fukalCyUZE7eydHKVRmtxKy5OuT0mhvUcAnAlpbB8odqbzcv9TT84H-DrxZw-U0v/pub?output=xlsx')
   df_monitoring['timestamp']=pd.to_datetime(df_monitoring['timestamp'])
   cols=[c for c in df_monitoring.columns if c not in ['timestamp']]
   for c in cols:
      df_monitoring[c]=df_monitoring[c].astype(str).str.replace(',','.').astype(float)
   df_monitoring=df_monitoring[df_monitoring.timestamp>df_monitoring.timestamp.max()-pd.Timedelta(hours=nb_hours)]
   df_monitoring['gain_theoretical']=df_monitoring['gain_theoretical']-df_monitoring['gain_theoretical'].values[0]
   

   df_invest=pd.read_excel('https://docs.google.com/spreadsheets/d/e/2PACX-1vSTqIh7BXEaPKj1fukalCyUZE7eydHKVRmtxKy5OuT0mhvUcAnAlpbB8odqbzcv9TT84H-DrxZw-U0v/pub?output=xlsx',sheet_name='current_invest')
   for c in ['usdc_borrowed','usdc_invested','pending_profit']:
      df_invest[c]=df_invest[c].astype(str).str.replace(',','.').astype(float)

   #computing basic info
   df_last_24h=df_monitoring.loc[df_monitoring.timestamp>pd.to_datetime(datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)-datetime.timedelta(days=1))]
   dt=pd.to_datetime(datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None))-pd.to_datetime(df_monitoring['timestamp'].values[-1])
   dt_min=dt.days*24*60+dt.seconds/60

   ##balance
   tot_usdc=df_monitoring['tot_usdc'].values[-1]
   max_usdc_seen=df_monitoring['tot_usdc'].max()
   tot_usdc_initial=df_monitoring['tot_usdc'].values[0]
   usdc_threshold=df_monitoring['usdc_threshold'].values[-1]
   remaining=tot_usdc-usdc_threshold
   risk_ratio=(tot_usdc-usdc_threshold)/(max_usdc_seen-usdc_threshold)

   ##profit
   gain_theoretical=df_monitoring['gain_theoretical'].values[-1]
   pending_profit=df_monitoring['pending_profit'].values[-1]
   gain_total=tot_usdc-tot_usdc_initial
   gain_24h=tot_usdc-df_last_24h['tot_usdc'].values[0]
   usdc_invested=df_monitoring['usdc_invested'].values[-1]
   usdc_borrowed=df_monitoring['usdc_borrowed'].values[-1]
   accuracy=df_monitoring['accuracy'].values[-1]
   tax=df_monitoring['tax'].values[-1]
   total_fees_usdc=df_monitoring['total_fees_usdc'].sum()
   interest_fees_usdc=df_monitoring['interest_fees_usdc'].sum()
   transac_fees_usdc=total_fees_usdc-interest_fees_usdc
   df_monitoring=df_monitoring.reset_index(drop=False).rename(columns={'index':'count_index'})
   df_monitoring['count_index']+=1

   ##market
   df_monitoring['btc_change']=100*(df_monitoring['price_btc']-df_monitoring['price_btc'].values[0])/df_monitoring['price_btc'].values[0]
   df_monitoring['mean_price_diff']=df_monitoring['mean_price_diff'].cumsum()*100
   market_total=df_monitoring['mean_price_diff'].values[-1]
   market_24h=market_total-df_last_24h['mean_price_diff'].values[0]  


   #Printing infos
   ##time
   color_dt='red'
   if dt_min < 10:
      color_dt='green'
   time=df_monitoring['timestamp'].values[-1]
   time=pd.to_datetime(time)
   st.markdown(f"<div style='text-align: center;'><b><font size='5' color='{color_dt}'>{time}</font>  </b></div>",unsafe_allow_html=True)

   ##balance and profit
   color_gain='red'
   if gain_total>=0:
      color_gain='green'
   color_pending='green'
   if pending_profit < 0:
      color_pending='red'
   color_gain_theoretical='red'
   if gain_theoretical>=0:
      color_gain_theoretical='green'
   st.markdown(f"<div style='text-align: center;'>Balance={tot_usdc:.2f}$  -  Gain total=<font color='{color_gain}' ><b>{gain_total:.2f}$</b></font> - Gain Theoretical=<font color='{color_gain_theoretical}'><b>{gain_theoretical:.2f}$</b> </font></div>",unsafe_allow_html=True)
   st.markdown(f"<div style='text-align: center;'>Borrowed={usdc_borrowed:.0f}$  -  Invested={usdc_invested:.0f}$ - Pending=<font color='{color_pending}' ><b>{pending_profit:.2f}$</b></font></div>",unsafe_allow_html=True)

   ##risk
   color_remaining='green'
   if risk_ratio < 0.33:
      color_remaining='red'
   elif risk_ratio<0.66:
      color_remaining='orange'
   st.markdown(f"<div style='text-align: center;'>Remaining=<font color='{color_remaining}'><b>{remaining:.0f}$</b></font> - Threshold={usdc_threshold:.0f}$</div>",unsafe_allow_html=True)

   ##Accuracy
   st.markdown(f"<div style='text-align: center;'>Accuracy={accuracy*100:.2f}%  - Tax={tax*100:.2f}% - Interest={interest_fees_usdc:.2f}$  </font></div>",unsafe_allow_html=True)

   ##MArket
   color_market_24h='red'
   if market_24h>0:
      color_market_24h='green'
   color_market_total='red'
   if market_total>0:
      color_market_total='green'
   st.markdown(f"<div style='text-align: center;'>Market total=<font color='{color_market_total}'><b>{market_total:.2f}%</b></font> - Market 24h=<font color='{color_market_24h}'><b>{market_24h:.2f}%</b></font></div>",unsafe_allow_html=True)


   ########################################
   #Figure 1: profit
   ########################################
   fig, axs= plt.subplots(nrows=1,ncols=1,figsize=(8,4))
   df_monitoring['max_usdc']=tot_usdc
   if df_monitoring.shape[0]>1:
      df_monitoring['max_usdc']=df_monitoring.rolling(df_monitoring.shape[0],min_periods=1).tot_usdc.max()
   p=axs.plot(df_monitoring['timestamp'],df_monitoring['gain_theoretical'],label=f'gain theoretical={gain_theoretical:.0f}$')
   p=axs.plot(df_monitoring['timestamp'],df_monitoring['tot_usdc']-tot_usdc_initial,label=f'balance={tot_usdc:.0f}$')
   axs.plot(df_monitoring['timestamp'],df_monitoring['max_usdc']-tot_usdc_initial,color=p[0].get_color(),linestyle='--',label=f'max={df_monitoring["max_usdc"].values[-1]:.0f}$')
   #axs.plot(df_monitoring['timestamp'],df_monitoring['usdc_threshold'].astype(float),label=f'threshold={usdc_threshold:.0f}$')
   axs.set_ylabel('Balance ($)')
   axs.grid(axis='y')
   axs.legend(loc='upper left',fontsize=12)
   axs.tick_params('x',labelrotation=45)
   fig.tight_layout()
   st.pyplot(fig)

   ########################################
   #Figure 2: investment
   ########################################
   fig, axs= plt.subplots(nrows=1,ncols=1,figsize=(8,4))
   p=axs.plot(df_monitoring['timestamp'],df_monitoring['usdc_borrowed'],label=f'borrowed={usdc_borrowed:.0f}$')
   ma=df_monitoring['usdc_borrowed'].cumsum()/df_monitoring['count_index']
   axs.plot(df_monitoring['timestamp'],ma,linestyle='dashed',color=p[0].get_color(),label=f'MA={ma.values[-1]:.0f}$')
   axs.set_ylabel('Investment ($)')
   axs.legend(loc='upper left',fontsize=12)
   axs.tick_params('x',labelrotation=45)
   fig.tight_layout()
   st.pyplot(fig)

   ########################################
   #Figure 2: investment
   ########################################
   fig, axs= plt.subplots(nrows=1,ncols=1,figsize=(8,4))
   p=axs.plot(df_monitoring['timestamp'],df_monitoring['usdc_invested'],label=f'invested={usdc_invested:.0f}$')
   ma=df_monitoring['usdc_invested'].cumsum()/df_monitoring['count_index']
   axs.plot(df_monitoring['timestamp'],ma,linestyle='dashed',color=p[0].get_color(),label=f'MA={ma.values[-1]:.0f}$')
   axs.set_ylabel('Investment ($)')
   axs.legend(loc='upper left',fontsize=12)
   axs.tick_params('x',labelrotation=45)
   fig.tight_layout()
   st.pyplot(fig)

   ########################################
   #Figure 3: investment per symbol
   ########################################
   fig, axs= plt.subplots(nrows=1,ncols=1,figsize=(8,4))
   df=df_invest[['asset','usdc_borrowed']].set_index('asset')
   df.plot.bar(ax=axs,color=['grey'])

   df=df_invest[['asset','usdc_invested']].set_index('asset')
   df.plot.bar(ax=axs,color=['royalblue'])

   df=df_invest[['asset','pending_profit']].set_index('asset').copy()
   r=np.where(df['pending_profit']>=0)[0]
   c=np.where(df.columns=='pending_profit')[0]
   df.iloc[r,c]=np.nan
   df.plot.bar(ax=axs,color=['red'])

   df=df_invest[['asset','pending_profit']].set_index('asset').copy()
   r=np.where(df['pending_profit']<0)[0]
   c=np.where(df.columns=='pending_profit')[0]
   df.iloc[r,c]=np.nan
   df.plot.bar(ax=axs,color=['green'])


   axs.grid(axis='y')
   axs.legend(loc='upper right',fontsize=8)
   axs.set_ylabel('Profit')
   fig.tight_layout()
   st.pyplot(fig)

   ########################################
   #Figure 4: market change
   ########################################


   df=df_monitoring.copy()
   df['real_profit']=(df['tot_usdc']-tot_usdc_initial)/tot_usdc_initial*100
   window_size=max(1,int(df.shape[0]/1000))
   df['btc_change_smoothed']=df['btc_change'].rolling(window_size).mean()
   df['market_mean_price_diff_smoothed']=df['mean_price_diff'].rolling(window_size).mean()
   df['real_profit_smoothed']=df['real_profit'].rolling(window_size).mean()

   fig, axs= plt.subplots(figsize=(8,4))
   ln1=axs.plot(df['timestamp'],df['btc_change_smoothed'],'blue',label=f'btc change (={df["btc_change"].values[-1]:.2f}%)')
   ln2=axs.plot(df['timestamp'],df['market_mean_price_diff_smoothed'],'green',label=f'market change (={df["mean_price_diff"].values[-1]:.2f}%)')
   ln3=axs.plot(df['timestamp'],df['real_profit_smoothed'],'r',label=f'profit variation (={df["real_profit"].values[-1]:.2f}%)')
   axs.set_ylabel('Variation (%)')
   axs.legend(loc='upper left',fontsize=12)
   axs.tick_params('x',labelrotation=45)
   fig.tight_layout()
   st.pyplot(fig)


   ########################################
   #Figure 5: Accuracy
   ########################################
   fig, axs= plt.subplots(figsize=(8,4))
   axs.plot(df_monitoring['timestamp'],df_monitoring['accuracy']*100,label=f'accuracy(={accuracy*100:.2f}%)')
   axs.set_ylabel('Accuracy (%)')
   axs.legend(loc='upper left',fontsize=12)
   axs.tick_params('x',labelrotation=45)
   fig.tight_layout()
   st.pyplot(fig)

   ########################################
   #Figure 6: Interest
   ########################################
   fig, axs= plt.subplots(figsize=(8,4))

   axs.plot(df_monitoring['timestamp'],df_monitoring['total_fees_usdc'].cumsum(),label=f'total fees(={total_fees_usdc:.2f}$)')
   axs.plot(df_monitoring['timestamp'],df_monitoring['interest_fees_usdc'].cumsum(),label=f'interest fees(={interest_fees_usdc:.2f}$)')
   axs.plot(df_monitoring['timestamp'],df_monitoring['total_fees_usdc'].cumsum()-df_monitoring['interest_fees_usdc'].cumsum(),label=f'transaction fees(={transac_fees_usdc:.2f}$)')
   axs.set_ylabel('Interest ($)')
   axs.legend(loc='upper left',fontsize=12)
   axs.tick_params('x',labelrotation=45)
   fig.tight_layout()
   st.pyplot(fig)

   ########################################
   #Figure 7: Borrowable?
   ########################################
   fig, axs= plt.subplots(figsize=(8,4))
   axs.plot(df_monitoring['timestamp'],df_monitoring['nb_y2h_less_1_percent'].cumsum()/df_monitoring['count_index'],label=f'nb y 5m < 1%')
   axs.set_ylabel('Number')
   axs.legend(loc='upper left',fontsize=12)
   axs.tick_params('x',labelrotation=45)
   fig.tight_layout()
   st.pyplot(fig)

   fig, axs= plt.subplots(figsize=(8,4))
   axs.plot(df_monitoring['timestamp'],df_monitoring['nb_borrowable_y2h_less_1_percent'].cumsum()/df_monitoring['nb_y2h_less_1_percent'].cumsum(),label=f'proba borrow')
   axs.set_ylabel('Probability')
   axs.legend(loc='upper left',fontsize=12)
   axs.tick_params('x',labelrotation=45)
   fig.tight_layout()
   st.pyplot(fig)