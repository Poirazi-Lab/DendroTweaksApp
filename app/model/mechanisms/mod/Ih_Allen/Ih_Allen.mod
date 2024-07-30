TITLE Hyperpolarization-activated cyclic nucleotide-gated (HCN) channel

COMMENT
 Reference:		Kole,Hallermann,and Stuart, J. Neurosci. 2006
ENDCOMMENT

NEURON	{
	SUFFIX Ih
	NONSPECIFIC_CURRENT ihcn
	RANGE gbar, ihcn
}

UNITS	{
	(mV) = (millivolt)
	(mA) = (milliamp)
	(S)  = (siemens)
}

PARAMETER	{
	gbar = 0.0    (S/cm2) 
	ehcn = -45.0  (mV)
	Ra   = 6.43   (/mV/ms)
	Rb   = 193    (/ms)
	v12a = -154.9 (mV)
	qa   = 11.9   (mV)
	qb   = 33.1   (mV)
}

ASSIGNED	{
	v    (mV)
	ihcn (mA/cm2)
	ghcn (S/cm2)
	mInf (1)
	mTau (ms)
}

STATE { m }

BREAKPOINT	{
	SOLVE states METHOD cnexp
	ghcn = gbar * m
	ihcn = ghcn * (v - ehcn)
}

DERIVATIVE states	{
	rates(v)
	m' = (mInf - m) / mTau
}

INITIAL{
	rates(v)
	m = mInf
}

FUNCTION vtrap(x(mV), y(mV)) (mV) { : Traps for 0 in denominator of rate equations
	if (fabs(x / y) < 1e-6) {
		vtrap = y * (1 - x / y / 2)
	} else {
		vtrap = x / (exp(x / y) - 1)
	}
}

PROCEDURE rates(v(mV)) {

	LOCAL mAlpha, mBeta

	mAlpha = Ra * vtrap(v - v12a, qa)
	mBeta = Rb * exp(v / qb)

	mInf = mAlpha / (mAlpha + mBeta)
	mTau = 1 / (mAlpha + mBeta)
}
