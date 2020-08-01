
import pygame
import random
import os
import time
import neat
pygame.font.init()  # init font

WIN_WIDTH = 600
WIN_HEIGHT = 800
FLOOR = 730
STAT_FONT = pygame.font.SysFont("comicsans", 50)
END_FONT = pygame.font.SysFont("comicsans", 70)

WIN = pygame.display.set_mode((WIN_WIDTH, WIN_HEIGHT))
pygame.display.set_caption("Flappy Bird")

# to double image size and load it
pipe_img = pygame.transform.scale2x(pygame.image.load(os.path.join("imgs","pipe.png")).convert_alpha())
bg_img = pygame.transform.scale(pygame.image.load(os.path.join("imgs","bg.png")).convert_alpha(), (600, 900))
bird_images = [pygame.transform.scale2x(pygame.image.load(os.path.join("imgs","bird" + str(x) + ".png"))) for x in range(1,4)]
base_img = pygame.transform.scale2x(pygame.image.load(os.path.join("imgs","base.png")).convert_alpha())

gen = 0

# -----------------BIRD-------------------
class Bird:

    MAX_ROTATION = 25           # how much the bird will tilt when it moves up or down
    IMGS = bird_images
    ROT_VEL = 20                # how much it will rotate on each frame or every time we move the bird
    ANIMATION_TIME = 5          # how long we'll show each bird animation, change how fast or slow bird flaps its wings

    def __init__(self, x, y):

        # position of the bird
        self.x = x
        self.y = y

        self.tilt = 0           # degrees to tilt
        self.tick_count = 0     # when we last jumped
        self.vel = 0
        self.height = self.y
        self.img_count = 0      # which bird image we're showing
        self.img = self.IMGS[0]

    def jump(self):

        self.vel = -10.5        # to go upwards and positive to go downwards
        self.tick_count = 0     # need to know when we changed direction or velocity for the physics
        self.height = self.y    # where the bird jumped from last

    def move(self):

        # tick happened and frame went by, keep track of how many times we moved since we last jumped
        self.tick_count += 1

        # for downward acceleration : how many pixels we move up or down in this frame
        displacement = self.vel*(self.tick_count) + 0.5*(3)*(self.tick_count)**2  # d = v * t + 3/2 * (t)^2

        # terminal velocity
        if displacement >= 16:       # if d is more than 16px downwards slow down
            displacement = (displacement/abs(displacement)) * 16

        if displacement < 0:         # if you're moving upwards move a little more (jumps higher)
            displacement -= 2

        self.y = self.y + displacement      # add displacement to current position

        if displacement < 0 or self.y < self.height + 50:  # tilt up
            if self.tilt < self.MAX_ROTATION:              # make sure no tilting too much
                self.tilt = self.MAX_ROTATION
        else:  # tilt down
            if self.tilt > -90:
                self.tilt -= self.ROT_VEL

    def draw(self, win):
        """
        draw the bird
        :param win: pygame window or surface
        :return: None
        """
        self.img_count += 1         # for animation we need to know how many times we've shown one image

        # For animation of bird, loop through three images
        # prevent one image from showing for too long

        if self.img_count <= self.ANIMATION_TIME:
            self.img = self.IMGS[0]
        elif self.img_count <= self.ANIMATION_TIME*2:
            self.img = self.IMGS[1]
        elif self.img_count <= self.ANIMATION_TIME*3:
            self.img = self.IMGS[2]
        elif self.img_count <= self.ANIMATION_TIME*4:
            self.img = self.IMGS[1]
        elif self.img_count == self.ANIMATION_TIME*4 + 1:
            self.img = self.IMGS[0]
            self.img_count = 0

        # so when bird is nose diving it isn't flapping
        if self.tilt <= -80:
            self.img = self.IMGS[1]
            self.img_count = self.ANIMATION_TIME*2

        # tilt the bird
        blitRotateCenter(win, self.img, (self.x, self.y), self.tilt)

    def get_mask(self):
        return pygame.mask.from_surface(self.img)

# ----------------------PIPE------------------------
class Pipe():

    # bird doesn't move, all other objects move
    GAP = 170
    VEL = 5

    def __init__(self, x):

        self.x = x
        self.height = 0

        # where the top and bottom of the pipe is
        self.top = 0
        self.bottom = 0

        self.PIPE_TOP = pygame.transform.flip(pipe_img, False, True)
        self.PIPE_BOTTOM = pipe_img

        self.passed = False

        self.set_height()

    def set_height(self):                                       # defines where out bottom and top pipes will be placed (how long they are)

        self.height = random.randrange(50, 450)                 # where the top of our pipe should be
        self.top = self.height - self.PIPE_TOP.get_height()     # push up the top left part of the image
        self.bottom = self.height + self.GAP                    # bring down top left by gap amount, thus add

    def move(self):  # old pipes keep moving towards left

        self.x -= self.VEL

    def draw(self, win):

        # draw top
        win.blit(self.PIPE_TOP, (self.x, self.top))
        # draw bottom
        win.blit(self.PIPE_BOTTOM, (self.x, self.bottom))

    # mask is basically 2D array of pixels of an image determining
    # where the actual pixels exist in the transparent image
    # comparisons of two masks, will let us know if they collide
    def collide(self, bird, win):

        bird_mask = bird.get_mask()
        top_mask = pygame.mask.from_surface(self.PIPE_TOP)
        bottom_mask = pygame.mask.from_surface(self.PIPE_BOTTOM)

        # offset: how far away these masks are
        top_offset = (self.x - bird.x, self.top - round(bird.y))
        bottom_offset = (self.x - bird.x, self.bottom - round(bird.y))

        # find point of collision, if no collision then None returned
        # point of overlap between bird mask and pipe using offset
        b_point = bird_mask.overlap(bottom_mask, bottom_offset)
        t_point = bird_mask.overlap(top_mask, top_offset)

        if b_point or t_point:
            return True

        return False

# -------------------BASE---------------------
class Base:

    VEL = 5
    WIDTH = base_img.get_width()
    IMG = base_img

    def __init__(self, y):      # x  position is going to be moving

        self.y = y
        self.x1 = 0
        self.x2 = self.WIDTH    # behind first image

    # we will have two base images
    # move both images to the left
    # at one point window will have both bases on the window
    # the point when the first base is completely out of the window we move it behind the 2nd image
    # (cyclic process)
    def move(self):

        # move it at a velocity
        self.x1 -= self.VEL
        self.x2 -= self.VEL

        # check if image is out of screen, if yes move it behind image
        if self.x1 + self.WIDTH < 0:
            self.x1 = self.x2 + self.WIDTH

        if self.x2 + self.WIDTH < 0:
            self.x2 = self.x1 + self.WIDTH

    def draw(self, win):

        win.blit(self.IMG, (self.x1, self.y))
        win.blit(self.IMG, (self.x2, self.y))


# rotate image about center instead of default topLeft
def blitRotateCenter(surf, image, topleft, angle):

    rotated_image = pygame.transform.rotate(image, angle)
    new_rect = rotated_image.get_rect(center = image.get_rect(topleft = topleft).center)

    surf.blit(rotated_image, new_rect.topleft)

# --------------DRAW WINDOW -----------------
def draw_window(win, birds, pipes, base, score, gen):

    if gen == 0:
        gen = 1
    win.blit(bg_img, (0,0))

    for pipe in pipes:
        pipe.draw(win)

    base.draw(win)

    for bird in birds:
        # draw bird
        bird.draw(win)

    # score
    score_label = STAT_FONT.render("Score: " + str(score),1,(255,255,255))
    win.blit(score_label, (WIN_WIDTH - score_label.get_width() - 15, 10))

    # generations
    score_label = STAT_FONT.render("Gens: " + str(gen-1),1,(255,255,255))
    win.blit(score_label, (10, 10))

    # alive
    score_label = STAT_FONT.render("Alive: " + str(len(birds)),1,(255,255,255))
    win.blit(score_label, (10, 50))

    pygame.display.update()


def eval_genomes(genomes, config):

    global WIN, gen
    win = WIN
    gen += 1

    # start by creating lists holding the genome itself, the
    # neural network associated with the genome and the
    # bird object that uses that network to play
    nets = []
    birds = []
    ge = []

    for genome_id, genome in genomes:
        genome.fitness = 0          # start with fitness level of 0
        net = neat.nn.FeedForwardNetwork.create(genome, config)     # setting up our neural network for our genome
        nets.append(net)
        birds.append(Bird(230, 350))
        ge.append(genome)

    base = Base(FLOOR)
    pipes = [Pipe(700)]
    score = 0

    clock = pygame.time.Clock()

    run = True
    while run and len(birds) > 0:
        clock.tick(30)                      # at most 30 frames every second

        for event in pygame.event.get():    # keep track of events happening like mouse click
            if event.type == pygame.QUIT:   # cross button
                run = False
                pygame.quit()
                quit()
                break

        pipe_ind = 0        # use pipe 1 as input into neural network

        if len(birds) > 0:
            if len(pipes) > 1 and birds[0].x > pipes[0].x + pipes[0].PIPE_TOP.get_width():      # determine whether to use the first or second
                pipe_ind = 1                                                                    # pipe on the screen for neural network input

        for x, bird in enumerate(birds):  # give each bird a fitness of 0.1 for each frame it stays alive
            ge[x].fitness += 0.1
            bird.move()

            # send bird location, top pipe location and bottom pipe location and determine from network whether to jump or not
            output = nets[birds.index(bird)].activate((bird.y, abs(bird.y - pipes[pipe_ind].height), abs(bird.y - pipes[pipe_ind].bottom)))

            # we get a list of outputs

            if output[0] > 0.5:  # we use a tanh activation function so result will be between -1 and 1. if over 0.5 jump
                bird.jump()

        base.move()

        rem = []
        add_pipe = False

        for pipe in pipes:
            pipe.move()
            # check for collision
            for bird in birds:
                if pipe.collide(bird, win):
                    ge[birds.index(bird)].fitness -= 1
                    nets.pop(birds.index(bird))
                    ge.pop(birds.index(bird))
                    birds.pop(birds.index(bird))

            if pipe.x + pipe.PIPE_TOP.get_width() < 0:      # if pipe is off the screen
                rem.append(pipe)

            if not pipe.passed and pipe.x < bird.x:         # check if pipe has been passed
                pipe.passed = True
                add_pipe = True

        if add_pipe:
            score += 1

            for genome in ge:
                genome.fitness += 5
            pipes.append(Pipe(WIN_WIDTH))

        for r in rem:
            pipes.remove(r)

        # if we hit the ground or fly too high
        # remove all info related to the bird, if it falls down
        for bird in birds:
            if bird.y + bird.img.get_height() - 10 >= FLOOR or bird.y < -50:
                nets.pop(birds.index(bird))
                ge.pop(birds.index(bird))
                birds.pop(birds.index(bird))

        draw_window(WIN, birds, pipes, base, score, gen)

def run(config_file):
    # sub-heading and properties we're setting
    config = neat.config.Config(neat.DefaultGenome, neat.DefaultReproduction,
                         neat.DefaultSpeciesSet, neat.DefaultStagnation,
                         config_file)

    # Create the population
    p = neat.Population(config)

    # show progress and stats
    p.add_reporter(neat.StdOutReporter(True))
    stats = neat.StatisticsReporter()
    p.add_reporter(stats)

    # Run for up to 50 generations.
    winner = p.run(eval_genomes, 50)

    # show final stats
    print('\nBest genome:\n{!s}'.format(winner))


if __name__ == '__main__':

    local_dir = os.path.dirname(__file__)
    config_path = os.path.join(local_dir, 'config_feedforward.txt')
    run(config_path)