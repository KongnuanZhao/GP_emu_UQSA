import gp_emu_uqsa.design_inputs as _gd
import gp_emu_uqsa._emulatorclasses as __emuc
import numpy as _np
import matplotlib.pyplot as _plt
from ._hmutilfunctions import *

def imp_plot(emuls, zs, cm, var_extra, maxno=1, olhcmult=100, grid=10, act=[], fileStr="", plot=True):
    """Create an implausibility and optical depth plot, made of subplots for each pair of active inputs (or only those specified). Implausibility plots in the lower triangle, optical depth plots in the upper triangle. The diagonal is blank, and implausibility plots are paired with optical depth plots across the diagonal.

    Args:
        emuls (Emulator list): list of Emulator instances
        zs (float list): list of output values to match
        cm (float list): cut-off for implausibility
        var_extra (float list): extra (non-emulator) variance on outputs
        maxno (int): which maximum implausibility to consider, default 1
        olhcmult (int): option for size of oLHC design across other inputs not in the considered pair, size = olhcmult*(no. active inputs - 2), default 100
        grid (int): divisions of each input range to make, with values of each input for a subplot centred on the gridpoint, default 10
        act (int list): list of active inputs for plot, default [] (all inputs)
        fileStr (str): string to prepend to output files, default ""
        plot (bool): choice to plot (e.g. False for batches), default True

    Returns:
        None

    """

    sets, minmax, orig_minmax = emulsetup(emuls)
    check_act(act, sets)
    act_ref = ref_act(minmax)
    plt_ref = ref_plt(act)

    num_inputs = len(minmax) # number of inputs we'll look at
    dim = num_inputs - 2 # dimensions of input that we'll change with oLHC

    maxno=int(maxno)
    IMP , ODP = [], [] ## need an IMP and ODP for each I_max
    for i in range(maxno):
        IMP.append( _np.zeros((grid,grid)) )
        ODP.append( _np.zeros((grid,grid)) )

    ## space for all plots, and reference index to subplot indices
    print("Creating plot objects... may take some time...")
    plot = True if plot == True else False
    rc = num_inputs if act == [] else len(act)
    if plot:
        fig, ax = _plt.subplots(nrows = rc, ncols = rc)
    plot_ref = act_ref if act == [] else ref_plt(act)

    ## reduce sets to only the chosen ones
    less_sets = []
    if act == []:
        less_sets = sets
    else:
        for s in sets:
            if s[0] in act and s[1] in act:
                less_sets.append(s)
    print("HM for input pairs:", less_sets)

    ## calculate plot for each pair of inputs
    for s in less_sets:
        print("\nset:", s)

        ## rows and columns of 2D grid for the {i,j} value of pair of inputs
        X1 = _np.linspace(minmax[str(s[0])][0], minmax[str(s[0])][1], grid, endpoint=False)
        X1 = X1 + 0.5*(minmax[str(s[0])][1] - minmax[str(s[0])][0])/float(grid)
        X2 = _np.linspace(minmax[str(s[1])][0], minmax[str(s[1])][1], grid, endpoint=False)
        X2 = X2 + 0.5*(minmax[str(s[1])][1] - minmax[str(s[1])][0])/float(grid)
        print("Values of the grid 1:" , X1)
        print("Values of the grid 2:" , X2)
        x_all=_np.zeros((grid*grid,2))
        for i in range(0,grid):
            for j in range(0,grid):
                x_all[i*grid+j,0] = X1[i]
                x_all[i*grid+j,1] = X2[j]

        ## use an OLHC design for all remaining inputs
        n = dim * int(olhcmult)  # no. of design_points
        N = int(n/2)  # number of designs from which 1 maximin is chosen
        olhc_range = [it[1] for it in sorted(minmax.items(), key=lambda x: int(x[0])) \
                      if int(it[0])!=s[0] and int(it[0])!=s[1]]
        print("olhc_range:", olhc_range)
        filename = "imp_input_"+str(s[0])+'_'+str(s[1])
        _gd.optLatinHyperCube(dim, n, N, olhc_range, filename)
        x_other_inputs = _np.loadtxt(filename) # read generated oLHC file in
        
        ## enough for ALL inputs - we'll mask any inputs not used by a particular emulator later
        x = _np.empty( [n , num_inputs] )

        ## stepping over the grid {i,j} to build subplot
        print("\nCalculating Implausibilities...")
        for i in range(0,grid):
            for j in range(0,grid):
                I2 = _np.zeros((n,len(emuls)))

                ## loop over outputs (i.e. over emulators)
                for o in range(len(emuls)):
                    E, z, var_e = emuls[o], zs[o], var_extra[o]
                    Eai = E.beliefs.active_index
                    ind_in_active=True if s[0] in Eai and s[1] in Eai else False
                    if ind_in_active:

                        ## set the input pair for this subplot
                        x[:,act_ref[str(s[0])]] = x_all[i*grid+j, 0]
                        x[:,act_ref[str(s[1])]] = x_all[i*grid+j, 1]

                        ## figure out what the other inputs active_indices are
                        other_dim = [act_ref[str(key)] for key in act_ref if int(key) not in s]
                        if len(other_dim) == 1:
                            x[:,other_dim] = _np.array([x_other_inputs,]).T
                        else:
                            x[:,other_dim] = x_other_inputs
                        
                        ## inactive inputs are masked
                        act_ind_list = [act_ref[str(l)] for l in Eai]
                        ni = __emuc.Data(x[:,act_ind_list],None,E.basis,E.par,E.beliefs,E.K)
                        post = __emuc.Posterior(ni, E.training, E.par, E.beliefs, E.K, predict=False)
                        mean = post.mean
                        var  = _np.diag(post.var)

                        ## calculate implausibility^2 values
                        for r in range(0,n):
                            I2[r,o] = ( mean[r] - z )**2 / ( var[r] + var_e )

                ## find maximum implausibility across different outputs
                I = _np.sqrt(I2)
                odp_count = _np.zeros(maxno,dtype=_np.uint32)
                Imaxes = _np.empty([n,maxno])
                for r in range(0,n):
                    Imaxes[r,:] = _np.sort(_np.partition(I[r,:],-maxno)[-maxno:])[-maxno:]
                    for m in range(maxno):
                        if Imaxes[r,-(m+1)] < cm: # check cut-off using this value
                            odp_count[m] = odp_count[m] + 1

                for m in range(maxno):
                    IMP[m][i,j] = _np.amin(Imaxes[:,-(m+1)]) # minimise across n points
                    ODP[m][i,j] = float(odp_count[m]) / float(n)

        ## save the results to file
        nfileStr = fileStr + "_" if fileStr != "" else fileStr
        for m in range(maxno): ## different file for each max
            _np.savetxt(nfileStr+str(m+1)+"_"+"IMP_"+str(s[0])+'_'+str(s[1]), IMP[m])
            _np.savetxt(nfileStr+str(m+1)+"_"+"ODP_"+str(s[0])+'_'+str(s[1]), ODP[m])

        if plot:
            make_plots(s, plt_ref, cm, maxno, ax, IMP, ODP, minmax=minmax)

    if plot:
        plot_options(plt_ref, ax, fig, minmax)
        _plt.show()

    return


def imp_plot_recon(cm, maxno=1, act=[], fileStr="", imp_cb=[], odp_cb=[]):
    """Reconstruct an implausibility and optical depth plot from the results files made using the imp_plot() function.

    Args:
        cm (float list): cut-off for implausibility
        maxno (int): which maximum implausibility to consider, default 1
        act (int list): list of active inputs for plot, default [] (all inputs)
        fileStr (str): string to prepend to output files, default ""

    Returns:
        None

    """

    if act == []:
        print("WARNING: Please specificy 'act' for active inputs. Return None.")
        return None

    print("Creating plot objects... may take some time...")
    fig, ax = _plt.subplots(nrows = len(act), ncols = len(act))
    plt_ref = ref_plt(act)

    sets = make_sets(act)
    print("HM for input pairs:", sets)

    try:
        [ivmin, ivmax] = [0.0, cm] if imp_cb == [] else imp_cb
        [ovmin, ovmax] = [None, None] if odp_cb == [] else odp_cb
    except ValueError as e:
        print("WARNING: invalid imp_cb and/or odp_cb supplied, setting to default.")
        [ivmin, ivmax] = [0.0, cm]
        [ovmin, ovmax] = [None, None]
    
    ## reload plot for each pair of inputs
    for s in sets:
        print("\nset:", s)

        nfileStr = fileStr + "_" if fileStr != "" else fileStr
        IMP = _np.loadtxt(nfileStr+str(maxno)+"_"+"IMP_"+str(s[0])+'_'+str(s[1]))
        ODP = _np.loadtxt(nfileStr+str(maxno)+"_"+"ODP_"+str(s[0])+'_'+str(s[1]))

        make_plots(s, plt_ref, cm, maxno, ax, IMP, ODP, recon=True,\
                   imp_cb=[ivmin, ivmax], odp_cb=[ovmin, ovmax])

    plot_options(plt_ref, ax, fig)
    _plt.show()

    return


def nonimp_data(emuls, zs, cm, var_extra, datafiles, maxno=1, act=[], fileStr=""):
    """Determine which inputs from a specified input file are non-implausible, and output these values (along with the corresponding outputs from a specified output file) to new files.

    Args:
        emuls (Emulator list): list of Emulator instances
        zs (float list): list of output values to match
        cm (float list): cut-off for implausibility
        var_extra (float list): extra (non-emulator) variance on outputs
        datafiles(str list): specify names of inputs and outputs files
        maxno (int): which maximum implausibility to consider, default 1
        act (int list): list of active inputs for plot, default [] (all inputs)
        fileStr (str): string to prepend to output files of non-implausible inputs and outputs, default ""

    Returns:
        nimp_inputs (int): number of non-implausible input points in input datafile

    """

    sets, minmax, orig_minmax = emulsetup(emuls)
    act_ref = ref_act(minmax)
    num_inputs = len(minmax)
    check_act(act, sets)
    maxno=int(maxno)

    sim_x, sim_y = load_datafiles(datafiles, orig_minmax)
    n = sim_x[:,0].size

    print("\nCalculating Implausibilities...")
    I2 = _np.zeros((n,len(emuls)))

    ## loop over outputs (i.e. over emulators)
    for o in range(len(emuls)):
        E, z, var_e = emuls[o], zs[o], var_extra[o]
        Eai = E.beliefs.active_index
        act_ind_list = [act_ref[str(l)] for l in Eai]

        ni = __emuc.Data(sim_x[:,act_ind_list],None,E.basis,E.par,E.beliefs,E.K)
        post = __emuc.Posterior(ni, E.training, E.par, E.beliefs, E.K, predict=False)
        mean = post.mean
        var  = _np.diag(post.var)

        ## calculate implausibility^2 values
        for r in range(0,n):
            I2[r,o] = ( mean[r] - z )**2 / ( var[r] + var_e )

    ## find maximum implausibility across different outputs
    I = _np.sqrt(I2)
    Imaxes = _np.empty([n,maxno])
    nimp_inputs, nimp_outputs = [], []
    for r in range(0,n):
        Imaxes[r,:] = _np.sort(_np.partition(I[r,:],-maxno)[-maxno:])[-maxno:]

        m = maxno-1
        if Imaxes[r,-(m+1)] < cm: # check cut-off using this value
            nimp_inputs.append(sim_x[r,:])
            nimp_outputs.append(sim_y[r,:])

    ## save the results to file
    nfileStr = fileStr + "_" if fileStr != "" else fileStr

    for m in range(maxno):
        _np.savetxt(nfileStr + "nonimp_" + datafiles[0], nimp_inputs)
        _np.savetxt(nfileStr + "nonimp_" + datafiles[1], nimp_outputs)

    print(len(nimp_inputs), "data points were non-implausible")

    return len(nimp_inputs)


def new_wave_design(emuls, zs, cm, var_extra, datafiles, maxno=1, olhcmult=100, act=[], fileStr=""):
    """Create a set of non-implausible design inputs to use for more simulations or experiments. Datafiles of non-implausible inputs (and corresponding outputs) should be provided so the design is optimised with respect to this data. An optimised Latin Hypercube design is made and only non-implausible inputs from this are kept. To adjust the design size while fixing cm, try adjusting olhcmult.

    Args:
        emuls (Emulator list): list of Emulator instances
        zs (float list): list of output values to match
        cm (float list): cut-off for implausibility
        var_extra (float list): extra (non-emulator) variance on outputs
        datafiles(str list): specify names of inputs and outputs files. These should be correspond to non-implausible inputs only; see nonimp_data() function 
        maxno (int): which maximum implausibility to consider, default 1
        olhcmult (int): option for size of oLHC design across other inputs not in the considered pair, size = olhcmult*(no. active inputs - 2), default 100
        act (int list): list of active inputs for plot, default [] (all inputs)
        fileStr (str): string to prepend to output files, default ""

    Returns:
        nimp_inputs (int): number of non-implausible design points created

    """

    sets, minmax, orig_minmax = emulsetup(emuls)
    act_ref = ref_act(minmax)
    check_act(act, sets)
    num_inputs = len(minmax)
    dim = num_inputs 
    maxno=int(maxno)
    
    sim_x, sim_y = load_datafiles(datafiles, orig_minmax)

    ## use an OLHC design for all remaining inputs
    n = dim * int(olhcmult)  # no. of design_points
    N = int(n/2)  # number of designs from which 1 maximin is chosen
    olhc_range = [it[1] for it in sorted(minmax.items(), key=lambda x: int(x[0]))] 
    print("olhc_range:", olhc_range)
    filename = "olhc_des"
    if sim_x == None:
        _gd.optLatinHyperCube(dim, n, N, olhc_range, filename)
    else:
        _gd.optLatinHyperCube(dim, n, N, olhc_range, filename, fextra=sim_x)
    x = _np.loadtxt(filename) # read generated oLHC file in

    print("\nCalculating Implausibilities...")
    I2 = _np.zeros((n,len(emuls)))

    ## loop over outputs (i.e. over emulators)
    for o in range(len(emuls)):
        E, z, var_e = emuls[o], zs[o], var_extra[o]
        Eai = E.beliefs.active_index
        act_ind_list = [act_ref[str(l)] for l in Eai]

        ni = __emuc.Data(x[:,act_ind_list],None,E.basis,E.par,E.beliefs,E.K)
        post = __emuc.Posterior(ni, E.training, E.par, E.beliefs, E.K, predict=False)
        mean = post.mean
        var  = _np.diag(post.var)

        ## calculate implausibility^2 values
        for r in range(0,n):
            I2[r,o] = ( mean[r] - z )**2 / ( var[r] + var_e )

    ## find maximum implausibility across different outputs
    I = _np.sqrt(I2)
    Imaxes = _np.empty([n,maxno])
    nimp_inputs = []
    for r in range(0,n):
        Imaxes[r,:] = _np.sort(_np.partition(I[r,:],-maxno)[-maxno:])[-maxno:]

        m = maxno-1
        if Imaxes[r,-(m+1)] < cm: # check cut-off using this value
            nimp_inputs.append(x[r,:])

    ## save the results to file
    nfileStr = fileStr + "_" if fileStr != "" else fileStr
    for m in range(maxno): ## different file for each max
        _np.savetxt(nfileStr + datafiles[0], nimp_inputs)

    print("Generated", len(nimp_inputs), "new data points")

    return len(nimp_inputs)

