### for the underlying sensistivity classes

import numpy as np
import matplotlib.pyplot as plt

class Sensitivity:
    def __init__(self, emul, v, m):
        print("This is the Sensitivity class being initialised")

        ## inputs stuff
        self.v = v
        self.m = m
        self.x = emul.training.inputs
        
        ## try to use exact values on the MUCM site
        if True:
            emul.par.delta = [[[ 0.5437, 0.0961 ]]]
            emul.par.sigma[0][0] = np.sqrt(0.9354)
            emul.par.beta = np.array([ 33.5981 , 4.8570 , -39.6695 ])
            emul.training.remake()

        #### init B
        self.B = np.linalg.inv(np.diag(self.v))
        print("B matrix:\n", self.B)

        #### init C
        self.C = np.diag( 1.0/(np.array(emul.par.delta[0][0])**2) )
        print("C matrix:\n", self.C)

        points = 1
        self.effect = np.zeros([points])
        self.xplot = np.linspace(0.0,1.0,points)
        j = 0
        for i in np.linspace(0.0,1.0,points):
            self.w = [1]
            self.xw = [i]
            
            self.wb = []
            for i in range(0,len(emul.par.delta[0][0])):
                if i not in self.w:
                    self.wb.append(i)
            #print("wb:",self.wb)

            self.H = emul.training.H
            self.A = emul.training.A ## my A may be different than MUCM - mine has already absorbed the sigma**2 into it...
            self.f = emul.training.outputs
            self.beta = emul.par.beta
            print("beta:",self.beta)
            self.sigma = emul.par.sigma[0][0] ## only taking the first sigma
            print("sigma:", self.sigma)


            ## we want to call these multiple times for different xw, get graph
            self.UPSQRT(self.w , self.xw)
            self.analyse(j)
            j=j+1

        plt.plot(self.xplot, self.effect , linewidth=2.0)
        if points > 1:
            plt.show()
    

    ### create UPSQRT for particular w and xw
    def UPSQRT(self, w, xw):

        ############# Tw #############
        self.T  = np.zeros([self.x[:,0].size])
        self.Tw = np.zeros([self.x[:,0].size])
        T1 = np.sqrt( self.B.dot(np.linalg.inv(self.B + 2.0*self.C)) ) 
        T2 = 0.5*2.0*self.C.dot(self.B).dot( np.linalg.inv(self.B + 2.0*self.C) )
        T3 = (self.x - self.m)**2
 
        Cww = np.diag(np.diag(self.C)[self.w])
        for k in range(0, self.x[:,0].size):
            self.T[k]  = np.prod( (T1.dot(np.exp(-T2.dot(T3[k]))))[self.wb] )
            self.Tw[k] = self.T[k]\
              *np.exp(-0.5*(xw-self.x[k][w]).T.dot(2.0*Cww).dot(xw-self.x[k][w]))


        ############# Rw #############
        self.R  = np.append([1.0], self.m)
        Rwno1 = np.array(self.m)
        Rwno1[w] = xw
        self.Rw = np.append([1.0], Rwno1)


        ############# Qw #############
        self.Q  = np.outer(self.R.T, self.R)
        self.Qw = np.zeros( [1+len(self.w+self.wb) , 1+len(self.w+self.wb)] )
        # fill in 1
        self.Qw[0][0] = 1.0
        # fill first row and column
        for i in self.wb + self.w:
            self.Qw[0][1+i] = self.m[i]
            self.Qw[1+i][0] = self.m[i]
        
        mwb_mwb = np.outer( self.m[self.wb], self.m[self.wb].T )
        #print( "m(wb)m(wb)^T :", mwb_mwb )
        for i in range(0,len(self.wb)):
            for j in range(0,len(self.wb)):
                self.Qw[1+self.wb[i]][1+self.wb[j]] = mwb_mwb[i][j]
        
        mwb_mw = np.outer( self.m[self.wb], self.m[self.w].T )
        #print( "m(wb)m(w)^T :", mwb_mw )
        for i in range(0,len(self.wb)):
            for j in range(0,len(self.w)):
                self.Qw[1+self.wb[i]][1+self.w[j]] = mwb_mw[i][j]

        mw_mwb = np.outer( self.m[self.w], self.m[self.wb].T )
        #print( "m(w)m(wb)^T :", mw_mwb )
        for i in range(0,len(self.w)):
            for j in range(0,len(self.wb)):
                self.Qw[1+self.w[i]][1+self.wb[j]] = mw_mwb[i][j]

        mw_mw = np.outer( self.m[self.w] , self.m[self.w].T )
        Bww = np.diag( np.diag(self.B)[self.w] )
        mw_mw_Bww = mw_mw + np.linalg.inv(Bww)
        #print( "m(w)m(w)^T + invBww :", mw_mw_Bww )
        for i in range(0,len(self.w)):
            for j in range(0,len(self.w)):
                self.Qw[1+self.w[i]][1+self.w[j]] = mw_mw_Bww[i][j]
        #print("Qw:\n",self.Qw)


        ############# Sw #############
        self.S  = np.outer(self.R.T, self.T)
        self.Sw = np.zeros( [ 1+len(self.w + self.wb) , self.x[:,0].size ] )
        S1 = np.sqrt( self.B.dot( np.linalg.inv(self.B + 2.0*self.C) ) ) 
        S2 = 0.5*(2.0*self.C*self.B).dot( np.linalg.inv(self.B + 2.0*self.C) )
        S3 = (self.x - self.m)**2

        for k in range( 0 , 1+len(self.w + self.wb) ):
            for l in range( 0 , self.x[:,0].size ):
                if k == 0:
                    E_star = 1.0
                else:
                    kn=k-1
                    if k-1 in self.wb:
                        E_star = self.m[kn]
                    if k-1 in self.w:
                        E_star=(2*self.C[kn][kn]*self.x[l][kn]\
                               +self.B[kn][kn]*self.m[kn])\
                               /( 2*self.C[kn][kn] + self.B[kn][kn] )
                self.Sw[k,l]=E_star*np.prod( S1.dot( np.exp(-S2.dot(S3[l])) ) )


        ############# Pw #############
        self.P  = np.outer(self.T.T, self.T)
        self.Pw = np.zeros([self.x[:,0].size , self.x[:,0].size])
        P1 = self.B.dot( np.linalg.inv(self.B + 2.0*self.C) )
        P2 = 0.5*2.0*self.C.dot(self.B).dot( np.linalg.inv(self.B + 2.0*self.C) )
        P3 = (self.x - self.m)**2
        P4 = np.sqrt( self.B.dot( np.linalg.inv(self.B + 4.0*self.C) ) )
        P5 = 0.5*np.linalg.inv(self.B + 4.0*self.C)

        for k in range( 0 , self.x[:,0].size ):
            for l in range( 0 , self.x[:,0].size ):
                P_prod = np.exp(-P2.dot( P3[k]+P3[l] ))
                self.Pw[k,l]=\
                    np.prod( (P1.dot(P_prod))[self.wb] )*\
                    np.prod( (P4.dot(\
                        np.exp( -P5.dot(\
                        4.0*(self.C*self.C).dot( (self.x[k]-self.x[l])**2 )\
                        +2.0*(self.C*self.B).dot(P3[k]+P3[l])) ) ))[self.w] )
        #print("Pw:" , self.Pw)


        ############# Uw #############
        self.U  = np.prod(np.diag( \
                np.sqrt( self.B.dot(np.linalg.inv(self.B+4.0*self.C)) ) ))
        self.Uw = np.prod(np.diag( \
                np.sqrt( self.B.dot(np.linalg.inv(self.B+4.0*self.C)) ))[self.wb])
        #print("U:", self.U, "Uw:", self.Uw)


    def analyse(self, i):
        print("This is the analyse function")

        ## have to compensate for MUCM def of A
        invA = np.linalg.inv(self.A/self.sigma**2)

        self.e = invA.dot(self.f - self.H.dot(self.beta))
            
        self.Emw = self.Rw.dot(self.beta) + self.Tw.dot(self.e)
        self.ME = (self.Rw-self.R).dot(self.beta) + (self.Tw-self.T).dot(self.e)
        print("xw:",self.xw,"ME_",self.w,":",self.ME)
        self.effect[i] = self.ME
        ## main effect is giving the correct results

        self.W = np.linalg.inv( (self.H.T).dot(invA).dot(self.H) )

        self.EEE = self.sigma**2 *\
             (\
                 self.Uw - np.trace(invA.dot(self.Pw))\
                 +   np.trace(self.W.dot(\
                     self.Qw - self.Sw.dot(invA).dot(self.H) -\
                     self.H.T.dot(invA).dot(self.Sw.T) +\
                     self.H.T.dot(invA).dot(self.Pw).dot(invA).dot(self.H)\
                                        )\
                             )\
             )\
             + (self.e.T).dot(self.Pw).dot(self.e)\
             + 2.0*(self.beta.T).dot(self.Sw).dot(self.e)\
             + (self.beta.T).dot(self.Qw).dot(self.beta)

        self.EE2 = self.sigma**2 *\
             (\
                 self.U - self.T.dot(invA).dot(self.T.T) +\
                 ( (self.R - self.T.dot(invA).dot(self.H)) )\
                 .dot( self.W )\
                 .dot( (self.R - self.T.dot(invA).dot(self.H)).T )\
             )\
             + ( self.R.dot(self.beta) + self.T.dot(self.e) )**2

        self.EV = self.EEE - self.EE2
        print("xw:",self.xw,"E(V_",self.w,"):",self.EV)

#        print(self.EE2)
#
#        self.EVf = self.sigma**2 *\
#            (\
#                self.U - self.T.dot(invA).dot(self.T.T) +\
#                 (self.R - self.T.dot(invA).dot(self.H)).dot(self.W).dot(\
#                    (self.R - self.T.dot(invA).dot(self.H)).T )\
#            ) 
#
#        print("EVf:", self.EVf)

        #self.EVTw = self.Vf #- "self.EV of the other index..."
        #print(self.Vf)

        ## find the problems in P, S, Q and W
        ## T and R must be correct because the other answers are correct...