"""
Kernels for particle filters

"""
import numpy as np
from scipy.special import expit

# Kernel
class Kernel(object):
    def __init__(self, **kwargs):
        self.parameters = kwargs.get('parameters', None)
        self.y_next = kwargs.get('y_next', None)
        return

    def set_parameters(self, parameters):
        self.parameters = parameters
        return

    def set_y_next(self, y_next):
        self.y_next = y_next
        return

    def sample_x0(self, prior_mean, prior_var, N, n):
        """ Initialize x_t

        Returns:
            x_t (N by n ndarray)
        """
        raise NotImplementedError()

    def rv(self, x_t, **kwargs):
        """ Sample x_{t+1} ~ K(x_{t+1} | x_t, parameters)

        Args:
            x_t (ndarray): N by n, x_t
            parameters (dict): parameters
        Return:
            x_next (ndarray): N by n, x_{t+1}

        """
        raise NotImplementedError()

    def reweight(self, x_t, x_next, **kwargs):
        """ Reweight function for Kernel

        weight_t = Pr(y_{t+1}, x_{t+1} | x_t, parameters) /
                    K(x_{t+1} | x_t, parameters)

        Args:
            x_t (ndarray): N by n, x_t
            x_next (ndarray): N by n, x_{t+1}
        Return:
            log_weights (ndarray): N, importance weights

        """
        raise NotImplementedError()

    def log_density(self, x_t, x_next, **kwargs):
        """ Density of kernel K(x_{t+1} | x_t, parameters)

        Args:
            x_t (N by n ndarray): x_t
            x_next (N by n ndarray): x_{t+1}

        Returns:
            loglikelihoods (N ndarray): K(x_next | x_t, parameters)
                (ignores constants with respect to x_t & x_next)
        """
        raise NotImplementedError()

    def get_prior_log_density_max(self):
        raise NotImplementedError()

# LatentGaussianKernel
class LatentGaussianKernel(Kernel):
    def sample_x0(self, prior_mean, prior_var, N, n):
        """ Initialize x_t

        Returns:
            x_t (N by n ndarray)
        """
        x_t = np.random.normal(
                loc=prior_mean,
                scale=np.sqrt(prior_var),
                size=(N, n))
        return x_t

    def prior_log_density(self, x_t, x_next, **kwargs):
        """ log density of prior kernel

        Args:
            x_t (N by n ndarray): x_t
            x_next (N by n ndarray): x_{t+1}

        Returns:
            loglikelihoods (N ndarray): q(x_next | x_t, parameters)
                (ignores constants with respect to x_t & x_next
        """
        N = np.shape(x_t)[0]
        if (len(np.shape(x_t)) > 1) and (np.shape(x_t)[1] > 1):
            # x is vector
            diff = x_next.T - np.dot(self.parameters.A, x_t.T)
            loglikelihoods = -0.5*np.sum(diff*np.dot(
                self.parameters.Qinv, diff), axis=0) - \
                        0.5*np.shape(x_t)[1] * np.log(2.0*np.pi) + \
                        np.sum(np.log(np.diag(self.parameters.LQinv)))
        else:
            # n = 1, x is scalar
            diff = x_next - self.parameters.A*x_t
            loglikelihoods = -0.5*(diff**2)*self.parameters.Qinv + \
                    -0.5*np.log(2.0*np.pi) + np.log(self.parameters.LQinv)
        loglikelihoods = np.reshape(loglikelihoods, (N))
        return loglikelihoods

    def get_prior_log_density_max(self):
        """ Return max value of log density based on current parameters

        Returns max_{x,x'} log q(x | x', parameters)
        """
        LQinv = self.parameters.LQinv
        n = np.shape(LQinv)[0]
        loglikelihood_max = -0.5*n*np.log(2.0*np.pi) + \
                np.sum(np.log(np.diag(LQinv)))
        return loglikelihood_max

# LGSSMKernels:
# Prior Kernel
class LGSSMPriorKernel(LatentGaussianKernel):
    """ Prior Kernel for LGSSM
        K(x_{t+1} | x_t) = Pr(x_{t+1} | x_t, parameters)
    """
    def rv(self, x_t, **kwargs):
        """ Prior Kernel for LGSSM

        Sample x_{t+1} ~ Pr(x_{t+1} | x_t, parameters)

        Args:
            x_t (ndarray): N by n, x_t
        Return:
            x_next (ndarray): N by n, x_{t+1}

        """
        if (len(np.shape(x_t)) > 1) and (np.shape(x_t)[1] > 1):
            # x is vector
            x_next_mean = x_t.dot(self.parameters.A.T)
            x_next = np.linalg.solve(self.parameters.LQinv.T,
                    np.random.normal(size=x_t.shape).T).T + x_next_mean
            return x_next
        else:
            # n = 1, x is scalar
            x_next_mean = x_t * self.parameters.A
            x_next = self.parameters.LQinv**-1 * np.random.normal(
                    size=x_t.shape) + x_next_mean
            return x_next

    def reweight(self, x_t, x_next, **kwargs):
        """ Reweight function for Prior Kernel for LGSSM

        weight_t = Pr(y_{t+1} | x_{t+1}, parameters)

        Args:
            x_t (ndarray): N by n, x_t
            x_next (ndarray): N by n, x_{t+1}
        Return:
            log_weights (ndarray): N, importance weights

        """
        N = np.shape(x_next)[0]
        if (len(np.shape(x_t)) > 1) and (np.shape(x_t)[1] > 1):
            # x is vector
            diff = np.outer(self.y_next, np.ones(N)) - \
                    np.dot(self.parameters.C, x_next.T)
            log_weights = \
                -0.5*np.shape(self.parameters.LRinv)[0]*np.log(2.0*np.pi) + \
                -0.5*np.sum(diff*np.dot(self.parameters.Rinv, diff), axis=0) + \
                np.sum(np.log(np.diag(self.parameters.LRinv)))
        else:
            # n = 1, x is scalar
            diff = self.y_next - self.parameters.C*x_next
            log_weights = \
                    -0.5*np.log(2.0*np.pi) + \
                    -0.5*(diff**2)*self.parameters.Rinv + \
                    np.log(self.parameters.LRinv)
        log_weights = np.reshape(log_weights, (N))
        return log_weights

# "Optimal" instrumental Kernel
class LGSSMOptimalKernel(LatentGaussianKernel):
    """ Optimal Instrumental Kernel for LGSSM
        K(x_{t+1} | x_t) = Pr(x_{t+1} | x_t, y_{t+1}, parameters)
    """
    def rv(self, x_t, **kwargs):
        """ optimal Kernel for LGSSM

        Sample x_{t+1} ~ Pr(x_{t+1} | x_t, y_{t+1}, parameters)

        Args:
            x_t (ndarray): N by n, x_t
        Return:
            x_next (ndarray): N by n, x_{t+1}

        """
        if (len(np.shape(x_t)) > 1) and (np.shape(x_t)[1] > 1):
            # x is vector
             raise NotImplementedError()
        else:
            # n = 1, x is scalar
            x_next_mean_precision = \
                    x_t * self.parameters.A * self.parameters.Qinv + \
                    self.y_next * self.parameters.C * self.parameters.Rinv
            x_next_precision = \
                    self.parameters.Qinv + \
                    (self.parameters.C**2)*self.parameters.Rinv

            x_next = (x_next_precision)**-0.5 * np.random.normal(
                    size=x_t.shape) + \
                    x_next_mean_precision/x_next_precision
            return x_next

    def reweight(self, x_t, x_next, **kwargs):
        """ Reweight function for Optimal Kernel for LGSSM

        weight_t = \Pr(y_t | x_{t-1}, parameters)

        Args:
            x_t (ndarray): N by n, x_t
            x_next (ndarray): N by n, x_{t+1}
        Return:
            log_weights (ndarray): N, importance weights

        """
        N = np.shape(x_next)[0]
        if (len(np.shape(x_t)) > 1) and (np.shape(x_t)[1] > 1):
            # x is vector
            raise NotImplementedError()
        else:
            # n = 1, x is scalar
            diff = self.y_next - self.parameters.A*x_t
            variance = self.parameters.Qinv**-1 + self.parameters.Rinv**-1
            log_weights = -0.5*(diff)**2 / variance - \
                    0.5*np.log(2.0*np.pi) - 0.5*np.log(variance)
        log_weights = np.reshape(log_weights, (N))
        return log_weights

class LGSSMHighDimOptimalKernel(LatentGaussianKernel):
    def set_parameters(self, parameters):
        self.parameters = parameters
        self._param = dict(
            AtQinv = np.dot(parameters.A.T, parameters.Qinv),
            CtRinv = np.dot(parameters.C.T, parameters.Rinv),
            CtRinvC = np.dot(parameters.C.T,
                np.dot(parameters.Rinv, parameters.C)
                ),
            )
        x_next_Lvar = np.linalg.inv(np.linalg.cholesky(
                parameters.Qinv + self._param['CtRinvC']
                )).T
        self._param['x_next_Lvar'] = x_next_Lvar
        self._param['x_next_var'] = np.dot(x_next_Lvar, x_next_Lvar.T)
        self._param['predictive_var'] = (self.parameters.R + np.dot(
                self.parameters.C,
                np.dot(self.parameters.Q, self.parameters.C.T),
                ))
        self._param['predictive_var_logdet'] = np.linalg.slogdet(
                self._param['predictive_var'])[1]
        return

    def rv(self, x_t, **kwargs):
        """ optimal Kernel for LGSSM

        Sample x_{t+1} ~ Pr(x_{t+1} | x_t, y_{t+1}, parameters)

        Args:
            x_t (ndarray): N by n, x_t
        Return:
            x_next (ndarray): N by n, x_{t+1}

        """
        if (len(np.shape(x_t)) > 1) and (np.shape(x_t)[1] > 1):
            # x is vector
            x_next_mean = np.dot(
                    np.dot(x_t, self._param['AtQinv']) +
                    np.outer(
                        np.ones(np.shape(x_t)[0]),
                        np.dot(self._param['CtRinv'], self.y_next),
                    ),
                    self._param['x_next_var']
                    )
            x_next = np.dot(
                    np.random.normal(size=x_t.shape),
                    self._param['x_next_Lvar'].T,
                    ) + x_next_mean
            return x_next
        else:
            raise NotImplementedError()

    def reweight(self, x_t, x_next, **kwargs):
        """ Reweight function for Optimal Kernel for LGSSM

        weight_t = \Pr(y_t | x_{t-1}, parameters)

        Args:
            x_t (ndarray): N by n, x_t
            x_next (ndarray): N by n, x_{t+1}
        Return:
            log_weights (ndarray): N, importance weights

        """
        N = np.shape(x_next)[0]
        if (len(np.shape(x_t)) > 1) and (np.shape(x_t)[1] > 1):
            # x is vector
            diff = \
                np.outer(np.ones(N), self.y_next) - np.dot(x_t, self.parameters.A)
            log_weights = (
                    -0.5*np.sum(diff *
                    np.linalg.solve(self._param['predictive_var'], diff.T).T,
                    axis=1) +\
                    -0.5*np.shape(x_t)[1]*np.log(2.0) + \
                    -0.5*self._param['predictive_var_logdet']
                    )
            return log_weights
        else:
            # n = 1, x is scalar
            raise NotImplementedError()

# SVM Kernels:
class SVMPriorKernel(LatentGaussianKernel):
    def rv(self, x_t, **kwargs):
        """ Prior Kernel for LGSSM

        Sample x_{t+1} ~ Pr(x_{t+1} | x_t, parameters)

        Args:
            x_t (ndarray): N by n, x_t
        Return:
            x_next (ndarray): N by n, x_{t+1}

        """
        if (len(np.shape(x_t)) > 1) and (np.shape(x_t)[1] > 1):
            # x is vector
            x_next_mean = x_t.dot(self.parameters.A.T)
            x_next = np.linalg.solve(self.parameters.LQinv.T,
                    np.random.normal(size=x_t.shape).T).T + x_next_mean
            return x_next
        else:
            # n = 1, x is scalar
            x_next_mean = x_t * self.parameters.A
            x_next = self.parameters.LQinv**-1 * np.random.normal(
                    size=x_t.shape) + x_next_mean
            return x_next

    def reweight(self, x_t, x_next, **kwargs):
        """ Reweight function for Prior Kernel for LGSSM

        weight_t = Pr(y_{t+1} | x_{t+1}, parameters)

        Args:
            x_t (ndarray): N by n, x_t
            x_next (ndarray): N by n, x_{t+1}
        Return:
            log_weights (ndarray): N, importance weights

        """
        N = np.shape(x_next)[0]
        if (len(np.shape(x_t)) > 1) and (np.shape(x_t)[1] > 1):
            # n > 1
            raise NotImplementedError()
        else:
            # n = 1, x is scalar
            diff = self.y_next
            log_weights = \
                    -0.5*np.log(2.0*np.pi) + \
                    -0.5*(diff**2)*np.exp(-x_next)*self.parameters.Rinv + \
                    np.log(self.parameters.LRinv) + \
                    -0.5*x_next
        log_weights = np.reshape(log_weights, (N))
        return log_weights

# Bernoulli SSM Kernels:
class BSSMPriorKernel(LatentGaussianKernel):
    def __init__(self, **kwargs):
        self.parameters = kwargs.get('parameters', None)
        y_next = kwargs.get('y_next', None)
        if y_next is not None:
            self.set_y_next(y_next)
        return

    def set_y_next(self, y_next):
        self.y_next = y_next[0]
        self.t_next = y_next[1]
        return

    def rv(self, x_t, **kwargs):
        """ Prior Kernel for LGSSM

        Sample x_{t+1} ~ Pr(x_{t+1} | x_t, parameters)

        Args:
            x_t (ndarray): N by n, x_t
        Return:
            x_next (ndarray): N by n, x_{t+1}

        """
        if (len(np.shape(x_t)) > 1) and (np.shape(x_t)[1] > 1):
            # x is vector
            x_next_mean = x_t.dot(self.parameters.A.T)
            x_next = np.linalg.solve(self.parameters.LQinv.T,
                    np.random.normal(size=x_t.shape).T).T + x_next_mean
            return x_next
        else:
            # n = 1, x is scalar
            x_next_mean = x_t * self.parameters.A
            x_next = self.parameters.LQinv**-1 * np.random.normal(
                    size=x_t.shape) + x_next_mean
            return x_next

    def reweight(self, x_t, x_next, **kwargs):
        """ Reweight function for Prior Kernel for LGSSM

        weight_t = Pr(y_{t+1} | x_{t+1}, parameters)

        Args:
            x_t (ndarray): N by n, x_t
            x_next (ndarray): N by n, x_{t+1}
        Return:
            log_weights (ndarray): N, importance weights

        """
        N = np.shape(x_next)[0]
        if (len(np.shape(x_t)) > 1) and (np.shape(x_t)[1] > 1):
            # n > 1
            raise NotImplementedError()
        else:
            # n = 1, x is scalar
            prob_next = expit(self.y_next * \
                    (x_next + self.parameters.s_t(self.t_next))
                    )
            log_weights = np.log(prob_next)
        log_weights = np.reshape(log_weights, (N))
        return log_weights

# GARCH Kernel:
class GARCHPriorKernel(Kernel):
    # n = 2, first dimension is x_t, second is sigma2_t
    def sample_x0(self, prior_mean, prior_var, N, **kwargs):
        """ Initialize x_t

        Returns:
            x_t (N by n ndarray)
        """
        x_t = np.zeros((N, 2))
        x_t[:,0] = np.random.normal(
                loc=prior_mean,
                scale=np.sqrt(prior_var),
                size=(N))
        return x_t

    def prior_log_density(self, x_t, x_next, **kwargs):
        """ log density of prior kernel

        Args:
            x_t (N by n ndarray): x_t
            x_next (N by n ndarray): x_{t+1}

        Returns:
            loglikelihoods (N ndarray): q(x_next | x_t, parameters)
                (ignores constants with respect to x_t & x_next
        """
        N = np.shape(x_next)[0]
        sigma2_next = self.parameters.alpha + \
                self.parameters.beta * x_t[:,0]**2 + \
                self.parameters.gamma * x_t[:,1]
        loglikelihoods = -0.5*x_next[:,0]**2/sigma2_next - \
                0.5 * np.log(2.0*np.pi) - 0.5 * np.log(sigma2_next)
        loglikelihoods = np.reshape(loglikelihoods, (N))
        return loglikelihoods

    def get_prior_log_density_max(self):
        """ Return max value of log density based on current parameters

        Returns max_{x,x'} log q(x | x', parameters)
        """
        alpha = self.parameters.alpha
        loglikelihood_max = -0.5*np.log(2.0*np.pi) + np.log(alpha)
        return loglikelihood_max

    def rv(self, x_t, **kwargs):
        """ Prior Kernel for GARCH

        Sample x_{t+1} ~ Pr(x_{t+1} | x_t, parameters)

        Args:
            x_t (ndarray): N by n, x_t
        Return:
            x_next (ndarray): N by n, x_{t+1}

        """
        N = np.shape(x_t)[0]
        sigma2_next = self.parameters.alpha + \
                self.parameters.beta * x_t[:,0]**2 + \
                self.parameters.gamma * x_t[:,1]

        x_next = np.zeros((N,2))
        x_next[:,0] = np.sqrt(sigma2_next) * np.random.normal(size=N)
        x_next[:,1] = sigma2_next
        return x_next

    def reweight(self, x_t, x_next, **kwargs):
        """ Reweight function for Prior Kernel for GARCH

        weight_t = Pr(y_{t+1} | x_{t+1}, parameters)

        Args:
            x_t (ndarray): N by n, x_t
            x_next (ndarray): N by n, x_{t+1}
        Return:
            log_weights (ndarray): N, importance weights

        """
        N = np.shape(x_next)[0]
        diff = self.y_next - x_next[:,0]
        log_weights = \
                -0.5*np.log(2.0*np.pi) + \
                -0.5*(diff**2)*self.parameters.Rinv + \
                np.log(self.parameters.LRinv)
        log_weights = np.reshape(log_weights, (N))
        return log_weights

class GARCHOptimalKernel(Kernel):
    # n = 2, first dimension is x_t, second is sigma2_t
    def sample_x0(self, prior_mean, prior_var, N, **kwargs):
        """ Initialize x_t

        Returns:
            x_t (N by n ndarray)
        """
        x_t = np.zeros((N, 2))
        x_t[:,0] = np.random.normal(
                loc=prior_mean,
                scale=np.sqrt(prior_var),
                size=(N))
        return x_t

    def prior_log_density(self, x_t, x_next, **kwargs):
        """ log density of prior kernel

        Args:
            x_t (N by n ndarray): x_t
            x_next (N by n ndarray): x_{t+1}

        Returns:
            loglikelihoods (N ndarray): q(x_next | x_t, parameters)
                (ignores constants with respect to x_t & x_next
        """
        N = np.shape(x_next)[0]
        sigma2_next = self.parameters.alpha + \
                self.parameters.beta * x_t[:,0]**2 + \
                self.parameters.gamma * x_t[:,1]
        loglikelihoods = -0.5*x_next[:,0]**2/sigma2_next - \
                0.5 * np.log(2.0*np.pi) - 0.5 * np.log(sigma2_next)
        loglikelihoods = np.reshape(loglikelihoods, (N))
        return loglikelihoods

    def get_prior_log_density_max(self):
        """ Return max value of log density based on current parameters

        Returns max_{x,x'} log q(x | x', parameters)
        """
        alpha = self.parameters.alpha
        loglikelihood_max = -0.5*np.log(2.0*np.pi) + np.log(alpha)
        return loglikelihood_max


    def rv(self, x_t, **kwargs):
        """ Optimal Kernel for GARCH

        Sample x_{t+1} ~ Pr(x_{t+1} | x_t, y_{t+1}, parameters)

        Args:
            x_t (ndarray): N by n, x_t
        Return:
            x_next (ndarray): N by n, x_{t+1}

        """
        N = np.shape(x_t)[0]
        sigma2_next = self.parameters.alpha + \
                self.parameters.beta * x_t[:,0]**2 + \
                self.parameters.gamma * x_t[:,1]

        x_next = np.zeros((N,2))

        var_next = (self.parameters.Rinv + sigma2_next**-1)**-1
        mean_next = var_next*(self.y_next * self.parameters.Rinv)
        x_next[:,0] = mean_next + np.sqrt(var_next) * np.random.normal(size=N)
        x_next[:,1] = sigma2_next
        return x_next

    def reweight(self, x_t, x_next, **kwargs):
        """ Reweight function for Optimal Kernel for GARCH

        weight_t = Pr(y_{t+1} | x_t, parameters)

        Args:
            x_t (ndarray): N by n, x_t
            x_next (ndarray): N by n, x_{t+1}
        Return:
            log_weights (ndarray): N, importance weights

        """
        N = np.shape(x_next)[0]
        diff = self.y_next
        var = x_next[:,1] + self.parameters.R
        log_weights = \
                -0.5*np.log(2.0*np.pi) + \
                -0.5*(diff**2)/var + \
                -0.5*np.log(var)
        log_weights = np.reshape(log_weights, (N))
        return log_weights





