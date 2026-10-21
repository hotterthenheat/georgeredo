"""LEAPS roll at 60 DTE vs 90 DTE: the theta cost by Black-Scholes (r 4%, q 0) of a 0.70-delta call held from 365 DTE
down to 60 vs 90, and the extra spread paid by rolling earlier; also 0.60/0.80 delta and IV 20%/40%."""
import math; from scipy.stats import norm
R=0.04
def bs(S,K,T,v): d1=(math.log(S/K)+(R+v*v/2)*T)/(v*math.sqrt(T)); return S*norm.cdf(d1)-K*math.exp(-R*T)*norm.cdf(d1-v*math.sqrt(T))
def K_for(S,T,v,d): d1=norm.ppf(d); return S*math.exp(-(d1*v*math.sqrt(T)-(R+v*v/2)*T))
S=100
print('delta IV  start  | time value at 365 / 120 / 90 / 60 / 30 DTE (spot unchanged) | decay 90->60 | decay 120->90 | daily theta at 90 and 60')
for d in [0.60,0.70,0.80]:
    for v in [0.20,0.40]:
        K=K_for(S,1.0,v,d); tv=lambda T: bs(S,K,T,v)-max(S-K*math.exp(-R*T),0)
        p=lambda T: bs(S,K,T,v)
        print(f'{d:.2f} {v:.2f} prem {p(1.0):6.2f} | TV {tv(1.0):5.2f} {tv(120/365):5.2f} {tv(90/365):5.2f} {tv(60/365):5.2f} {tv(30/365):5.2f} | {p(90/365)-p(60/365):5.2f} ({(p(90/365)-p(60/365))/p(1.0)*100:4.1f}% of the entry premium) | {p(120/365)-p(90/365):5.2f} | {(p(91/365)-p(89/365))/2:.3f} {(p(61/365)-p(59/365))/2:.3f} per day')
print('Rolling cost: one roll = one round trip of spread + 2 fees; at a 3% (ETF) / 8% (single) spread on a ~15-point 0.70-delta LEAPS mid that is ~0.45 / 1.2 points a roll.')
