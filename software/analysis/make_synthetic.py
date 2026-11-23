# Synthetic NanoVNA-style sweeps to test ice_ascan.py (25 cm ice, antenna 35 cm above it)
import numpy as np
C0=299_792_458.0; rng=np.random.default_rng(1)
f=np.arange(1,301)*0.02e9                         # 0.02-6 GHz, 20 MHz steps (as in Meng et al.)
H=np.exp(-((f-2.0e9)/1.1e9)**4)                   # antenna passband ~0.85-3.1 GHz
ring=0.6*np.exp(-2j*np.pi*f*0.35e-9)+0.3*np.exp(-2j*np.pi*f*0.8e-9)   # antenna ringing
eps=3.2; h_air=0.35; d=0.25
ts=2*h_air/C0; tb=ts+2*d*np.sqrt(eps)/C0
Rs=(1-np.sqrt(eps))/(1+np.sqrt(eps)); Rb=(np.sqrt(eps)-np.sqrt(80))/(np.sqrt(eps)+np.sqrt(80))
sp=0.3                                            # spreading loss factor
def noise(): return 2e-3*(rng.standard_normal(len(f))+1j*rng.standard_normal(len(f)))
sky  = H*ring+noise()
ice  = H*(ring+sp*Rs*np.exp(-2j*np.pi*f*ts)+sp*0.85*(1-Rs**2)*Rb*np.exp(-2j*np.pi*f*tb))+noise()
plate= H*(ring+sp*(-1)*np.exp(-2j*np.pi*f*ts))+noise()
def save(name,s):
    with open(name,'w') as fh:
        fh.write('# HZ S RI R 50\n')
        for fi,si in zip(f,s): fh.write(f'{fi:.0f} {si.real:.6e} {si.imag:.6e}\n')
for n,s in (('ice.s1p',ice),('sky.s1p',sky),('plate.s1p',plate)): save(n,s)
print(f'true surface {ts*1e9:.3f} ns, bottom {tb*1e9:.3f} ns, d={d*100} cm')
