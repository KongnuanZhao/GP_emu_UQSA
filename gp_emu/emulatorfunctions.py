import numpy as np
import gp_emu.emulatorclasses as emuc
import matplotlib.pyplot as plt

### returns the initialised config class
def config_file(f):
    print("config file:" , f)
    return emuc.Config(f)

### configure kernel with enough delta for all the kernels 
def auto_configure_kernel(K, par, all_data):
    dim = all_data.x_full[0].size
    d_list = []
    for d in range(0, len(K.var_list)):
        if K.name[d] != "Noise":
            d_per_dim = int(K.delta[d].flat[:].size/K.delta[d][0].size)
            gen = [[1.0 for i in range(0,dim)] for j in range(0,d_per_dim)]
            d_list.append(np.array(gen))
        else:
            d_list.append([])
    K.update_delta(d_list)
    K.numbers()

    ### if user has provided delta and sigma values, overwrite the above
    if par.delta != []:
        K.update_delta(par.delta)
    if par.sigma != []:
        K.update_sigma(par.sigma)


### builds the entire emulator and training structures
def setup(config, K):
    #### read from beliefs file
    beliefs = emuc.Beliefs(config.beliefs)
    par = emuc.Hyperparams(beliefs)
    basis = emuc.Basis(beliefs)

    #### split data T & V ; (k,c,noV) - no.sets, set for V, no.V.sets
    tv_conf = emuc.TV_config(*config.tv_config)
    all_data = emuc.All_Data(config.inputs,config.outputs,tv_conf,beliefs,par)

    auto_configure_kernel(K, par, all_data)

    #### build all emuclator structures from beliefs and data
    training = emuc.Data(*all_data.choose_T(), basis, par, beliefs, K)
    validation = emuc.Data(*all_data.choose_V(), basis, par, beliefs, K)
    post = emuc.Posterior(validation, training, par, beliefs, K)
    opt_T = emuc.Optimize(training, basis, par, beliefs, config)
    
    return emuc.Emulator\
        (beliefs,par,basis,tv_conf,all_data,training,validation,post,opt_T, K)

### rebuilds training, validation, and post
def rebuild(t, v, p):
    ###### rebuild data structures ######
    print("Building data structures")
    t.remake()
    v.remake()
    p.remake()


#### save emulator information to files
def new_belief_filenames(E, config):
    new_beliefs_file=\
      config.beliefs+"-"+str(E.tv_conf.no_of_trains)
    new_inputs_file=\
      config.inputs+"-"+str(E.tv_conf.no_of_trains)
    new_outputs_file=\
      config.outputs+"-"+str(E.tv_conf.no_of_trains)
    return(new_beliefs_file, new_inputs_file, new_outputs_file)


### trains and validates while there is still validation data left
def training_loop(E, config):
    while E.tv_conf.doing_training():
        E.opt_T.llhoptimize_full\
          (config.tries,config.constraints,config.bounds,config.stochastic)

        rebuild(E.training, E.validation, E.post)

        E.post.mahalanobis_distance()
        E.post.indiv_standard_error(ise=2.0)

        (nbf,nif,nof) = new_belief_filenames(E, config)
        E.beliefs.final_beliefs(nbf, E.par, E.all_data.minmax, E.K)
        E.post.final_design_points(nif,nof,E.all_data.minmax)

        if E.tv_conf.check_still_training():
            E.post.incVinT()
            E.tv_conf.next_Vset()
            E.all_data.choose_new_V(E.validation)
            rebuild(E.training, E.validation, E.post)

### does final training (including validation data) and saves to files
def final_build(E, config):
    if E.tv_conf.do_final_build():
        print("\n***Doing final build***")

        E.post.incVinT()
        E.training.remake()
        E.opt_T.llhoptimize_full\
          (config.tries,config.constraints,config.bounds,config.stochastic)
        E.training.remake()

    (nbf,nif,nof) = new_belief_filenames(E, config)
    E.beliefs.final_beliefs(nbf, E.par, E.all_data.minmax, E.K)
    E.post.final_design_points(nif,nof,E.all_data.minmax)


### full range of inputs to get full posterior -- call via plot
def full_input_range(dim,rows,cols,plot_dims,fixed_dims,fixed_vals,one_d):
    if dim>=2:
        if one_d!=True:
            RF = rows
            CF = cols
            X1 = np.linspace(0.0,1.0,RF)
            X2 = np.linspace(0.0,1.0,CF)
            x_all=np.zeros((RF*CF,dim))
            for i in range(0,RF):
                for j in range(0,CF):
                    x_all[i*CF+j,plot_dims[0]] = X1[i]
                    x_all[i*CF+j,plot_dims[1]] = X2[j]
            if dim>2:
                for i in range(0,len(fixed_dims)):
                    x_all[:,fixed_dims[i]] = fixed_vals[i]
        else:
            RF = rows*cols
            X1 = np.linspace(0.0,1.0,RF)
            x_all=np.zeros((dim,RF))
            x_all[:,plot_dims[0]] = X1
            if dim>1:
                for i in range(0,len(fixed_dims)):
                    x_all[:,fixed_dims[i]] = fixed_vals[i]
    else:
        RF = rows*cols
        X1 = np.linspace(0.0,1.0,RF)
        x_all=np.zeros((1,RF))
        x_all[:,0] = X1
    return x_all

### plotting function - should not be called directly, call plot instead
def plotting(dim, post, rows, cols, one_d, mean_or_var):
    if dim>=2 and one_d!=True:
        RF = rows
        CF = cols
        ## these are the full predicions in a form that can be plotted
        X1 = np.linspace(0.0,1.0,RF)
        X2 = np.linspace(0.0,1.0,CF)
        x_all=np.zeros((RF*CF,dim))
        for i in range(0,RF):
            for j in range(0,CF):
                x_all[i*CF+j,0] = X1[i]
                x_all[i*CF+j,1] = X2[j] 
        XF, YF = np.meshgrid(X1, X2)
        if mean_or_var != "var":
            prediction=post.newnewmean
        else:
            prediction=np.diag(post.newnewvar)
        ZF = np.zeros((RF,CF))
        LF = np.zeros((RF,CF))
        UF = np.zeros((RF,CF))
        for i in range(0,RF):
            for j in range(0,CF):
                ZF[i,j]=prediction[i*CF+j]
                LF[i,j]=post.LI[i*CF+j]
                UF[i,j]=post.UI[i*CF+j]

        print("Plotting... output range:", np.amin(ZF), "to" , np.amax(ZF))
        fig = plt.figure()
        
        im = plt.imshow(ZF.T, origin='lower',\
             cmap=plt.get_cmap('rainbow'), extent=(0.0,1.0,0.0,1.0))
        plt.colorbar()
        plt.show()
    else:
        RF = rows*cols
        ## these are the full predicions in a form that can be plotted
        X1 = np.linspace(0.0,1.0,RF)
        if mean_or_var != "var":
            prediction=post.newnewmean
        else:
            prediction=np.diag(post.newnewvar)
        ZF = np.zeros((RF))
        LF = np.zeros((RF))
        UF = np.zeros((RF))
        for i in range(0,RF):
                ZF[i]=prediction[i]
                LF[i]=post.LI[i]
                UF[i]=post.UI[i]

        print("Plotting... output range:", np.amin(ZF), "to" , np.amax(ZF))
        #fig = plt.figure()
       
        plt.plot(X1,ZF, linewidth=2.0)
        plt.show()

### plotting function 
def plot(E, plot_dims, fixed_dims, fixed_vals, mean_or_var="mean"):
    dim = E.training.inputs[0].size
    if input("\nPlot full prediction? y/[n]: ") == 'y':
        print("***Generating full prediction***")
        if len(plot_dims) == 1 and dim>1:
            one_d = True
        else:
            one_d =False
        pn=30 ### large range of x i.e. pnXpn points
        # which dims to 2D plot, list of fixed dims, and values of fixed dims
        full_xrange = full_input_range(dim, pn, pn,\
            plot_dims, fixed_dims, fixed_vals, one_d)
        predict = emuc.Data(full_xrange, 0, E.basis, E.par, E.beliefs, E.K) # don't pass y
        post = emuc.Posterior(predict, E.training, E.par, E.beliefs, E.K) # calc post with x as V
        plotting(dim, post, pn, pn, one_d, mean_or_var) ## plot
