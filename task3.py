import math
import numpy as np
import gym
from gym import spaces, logger
from gym.utils import seeding


class CartPoleEnv(gym.Env):
    metadata = {
        'render.modes': ['human', 'rgb_array'],
        'video.frames_per_second': 50
    }

    def __init__(self, case=1):
        self.__version__ = "0.2.0"
        print("CartPoleEnv - Version {}, Noise case: {}".format(self.__version__, case))
        self.gravity = 9.8
        self.masscart = 1.0
        self.masspole = 0.4
        self.total_mass = (self.masspole + self.masscart)
        self.length = 0.5
        self.polemass_length = (self.masspole * self.length)
        self.seed()

        #self.force_mag = 10.0
        self.force_mag = 10.0*(1+self.np_random.uniform(low=-0.30, high=0.30))

        self.tau = 0.02  # seconds between state updates
        self.frictioncart = 5e-4  # AA Added cart friction
        self.frictionpole = 2e-6  # AA Added cart friction
        self.gravity_eps = 0.99  # Random scaling for gravity
        self.frictioncart_eps = 0.99  # Random scaling for friction
        self.frictionpole_eps = 0.99  # Random scaling for friction

        # Angle at which to fail the episode
        self.theta_threshold_radians = 12 * 2 * math.pi / 360
        self.x_threshold = 2.4

        # Angle limit set to 2 * theta_threshold_radians so failing observation is still within bounds
        high = np.array([
            self.x_threshold * 2,
            np.finfo(np.float32).max,
            self.theta_threshold_radians * 2,
            np.finfo(np.float32).max])

        # AA Set discrete states back to 2
        self.action_space = spaces.Discrete(2)
        self.observation_space = spaces.Box(-high, high)

        self.viewer = None
        self.state = None

        self.steps_beyond_done = None

    def seed(self, seed=None):  # Set appropriate seed value
        self.np_random, seed = seeding.np_random(seed)
        return [seed]

    def step(self, action):
        assert self.action_space.contains(
            action), "%r (%s) invalid" % (action, type(action))
        state = self.state
        x, x_dot, theta, theta_dot = state
        force = self.force_mag if action == 1 else -self.force_mag
        costheta = math.cos(theta)
        sintheta = math.sin(theta)
        temp = (force + self.polemass_length * theta_dot * theta_dot * sintheta - self.frictioncart * (4 +
                                                                                                       self.frictioncart_eps*np.random.randn()) * np.sign(x_dot)) / self.total_mass  # AA Added cart friction
        thetaacc = (self.gravity * (4 + self.gravity_eps*np.random.randn()) * sintheta - costheta * temp - self.frictionpole * (4 + self.frictionpole_eps*np.random.randn())
                    * theta_dot/self.polemass_length) / (self.length * (4.0/3.0 - self.masspole * costheta * costheta / self.total_mass))  # AA Added pole friction
        xacc = temp - self.polemass_length * thetaacc * costheta / self.total_mass
        #noise = 0
        noise = self.np_random.uniform(low=-0.30, high=0.30)
        x = (x + self.tau * x_dot)
        x_dot = (x_dot + self.tau * xacc)
        theta = (theta + self.tau * theta_dot)*(1 + noise)
        theta_dot = (theta_dot + self.tau * thetaacc)
        self.state = (x, x_dot, theta, theta_dot)
        done = x < -self.x_threshold \
            or x > self.x_threshold \
            or theta < -self.theta_threshold_radians \
            or theta > self.theta_threshold_radians
        done = bool(done)

        if not done:
            reward = 1.0
        elif self.steps_beyond_done is None:
            # Pole just fell!
            self.steps_beyond_done = 0
            reward = 1.0
        else:
            if self.steps_beyond_done == 0:
                logger.warning("You are calling 'step()' even though this environment has already returned done = True. You should always call 'reset()' once you receive 'done = True' -- any further steps are undefined behavior.")
            self.steps_beyond_done += 1
            reward = 0.0

        return np.array(self.state), reward, done, {}

    def reset(self):
        self.state = self.np_random.uniform(low=-0.05, high=0.05, size=(4,))
        self.steps_beyond_done = None
        return np.array(self.state)

    def render(self, mode='human', close=False):
        if close:
            if self.viewer is not None:
                self.viewer.close()
                self.viewer = None
            return

        screen_width = 600
        screen_height = 400

        world_width = self.x_threshold*2
        scale = screen_width/world_width
        carty = 100  # TOP OF CART
        polewidth = 10.0
        polelen = scale * 1.0
        cartwidth = 50.0
        cartheight = 30.0

        if self.viewer is None:
            from gym.envs.classic_control import rendering
            self.viewer = rendering.Viewer(screen_width, screen_height)
            l, r, t, b = -cartwidth/2, cartwidth/2, cartheight/2, -cartheight/2
            axleoffset = cartheight/4.0
            cart = rendering.FilledPolygon([(l, b), (l, t), (r, t), (r, b)])
            self.carttrans = rendering.Transform()
            cart.add_attr(self.carttrans)
            self.viewer.add_geom(cart)
            l, r, t, b = -polewidth/2, polewidth/2, polelen-polewidth/2, -polewidth/2
            pole = rendering.FilledPolygon([(l, b), (l, t), (r, t), (r, b)])
            pole.set_color(.8, .6, .4)
            self.poletrans = rendering.Transform(translation=(0, axleoffset))
            pole.add_attr(self.poletrans)
            pole.add_attr(self.carttrans)
            self.viewer.add_geom(pole)
            self.axle = rendering.make_circle(polewidth/2)
            self.axle.add_attr(self.poletrans)
            self.axle.add_attr(self.carttrans)
            self.axle.set_color(.5, .5, .8)
            self.viewer.add_geom(self.axle)
            self.track = rendering.Line((0, carty), (screen_width, carty))
            self.track.set_color(0, 0, 0)
            self.viewer.add_geom(self.track)

        if self.state is None:
            return None

        x = self.state
        cartx = x[0]*scale+screen_width/2.0  # MIDDLE OF CART
        self.carttrans.set_translation(cartx, carty)
        self.poletrans.set_rotation(-x[2])
        return self.viewer.render(return_rgb_array=mode == 'rgb_array')
