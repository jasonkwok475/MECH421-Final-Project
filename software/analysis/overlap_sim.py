# Single antenna, 20 cm above 20 cm of ice: does the antenna's own reflection hide the echoes?
import numpy as np, matplotlib.pyplot as plt
from scipy.signal import windows
C0=299_792_458.0; eps=3.2; n=np.sqrt(eps)
gap=0.20; d=0.20
ts=2*gap/C0; tb=ts+2*d*n/C0
Rs=(1-n)/(1+n); Rb=(n-np.sqrt(80))/(n+np.sqrt(80))
def self_refl(f):  # antenna mismatch + ringing (decaying internal reflections)
    return sum(a*np.exp(-2j*np.pi*f*t) for a,t in [(0.25,0.15e-9),(0.12,0.6e-9),(0.06,1.1e-9),(0.03,1.7e-9)])
def sweep(f0,f1,npts,resid=0.0):
    f=np.linspace(f0,f1,npts); s0=self_refl(f)
    ice=s0*(1+resid)+0.15*Rs*np.exp(-2j*np.pi*f*ts)+0.15*0.9*(1-Rs**2)*Rb*np.exp(-2j*np.pi*f*tb)
    return f,ice,s0
def ascan(f,x):
    w=windows.hann(len(f)); nfft=8192
    tr=np.fft.ifft(x*w,nfft)*nfft/w.sum(); t=np.arange(nfft)/(nfft*(f[1]-f[0]))
    return t*1e9,20*np.log10(np.abs(tr)+1e-9)
cases=[("NanoVNA-H: 0.5–1.5 GHz",0.5e9,1.5e9,101),("LiteVNA/V2: 0.75–3.0 GHz",0.75e9,3.0e9,226)]
fig,ax=plt.subplots(2,1,figsize=(9,6.5),sharex=True)
for a,(name,f0,f1,N) in zip(ax,cases):
    f,ice,s0=sweep(f0,f1,N)
    t,raw=ascan(f,ice); _,sub=ascan(f,ice-s0)
    f,ice2,s02=sweep(f0,f1,N,resid=0.08)   # 8% change in antenna self-reflection (ice in near field)
    _,sub2=ascan(f,ice2-s02)
    m=t<8
    a.plot(t[m],raw[m],color="#adb5bd",lw=2,label="raw (no background subtraction)")
    a.plot(t[m],sub2[m],color="#f08c00",lw=1.6,label="subtracted, 8% near-field change")
    a.plot(t[m],sub[m],color="#d9480f",lw=2,label="subtracted, perfect")
    for x,l in ((ts*1e9,"ice surface"),(tb*1e9,"ice bottom")):
        a.axvline(x,color="#1c7ed6",ls="--",lw=1); a.text(x,-2,l,color="#1c7ed6",ha="center",va="top",fontsize=9)
    a.set_ylim(-50,-0); a.set_title(name,loc="left",fontsize=11); a.grid(alpha=.3); a.set_ylabel("Echo [dB]")
ax[0].legend(loc="upper right",fontsize=8.5); ax[1].set_xlabel("Two-way time [ns]")
fig.suptitle("One antenna, 20 cm above 20 cm of ice (simulated)",fontsize=12)
fig.tight_layout(); fig.savefig("single_antenna_overlap.png",dpi=180)
print(ts*1e9,tb*1e9)
