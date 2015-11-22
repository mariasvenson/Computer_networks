#! /usr/bin/python

import simpy, random


N=0           # initial queue length
lambd=15.0    # customers/hour
mu=20.0       # customers/hour
simtime=200.0 # run for 200 seconds

def schedule_new_event(env, cb_func, delay):
    ev = simpy.events.Event(env)
    ev.callbacks.append(cb_func)
    ev.ok = True
    env.schedule(ev, simpy.events.NORMAL, delay)


navg = 0.0
prev_t = 0.0
def update_avg(t, n):
    global navg, prev_t
    navg = navg + n * (t - prev_t)
    prev_t = t


def arrival(ev):
    global N
    update_avg(ev.env.now, N)
    N = N + 1
    print ev.env.now, "arr, N len", N
    if N == 1:
        schedule_new_event(ev.env, departure, random.expovariate(mu))
    schedule_new_event(ev.env, arrival, random.expovariate(lambd))


def departure(ev):
    global N
    update_avg(ev.env.now, N)
    N = N - 1
    print ev.env.now, "dep, N len", N
    if N > 0:
        schedule_new_event(ev.env, departure, random.expovariate(mu))


def run_once():
    env = simpy.Environment(0.0)
    schedule_new_event(env, arrival,
                       random.expovariate(lambd))
    env.run(until=simtime)
    update_avg(simtime, N)
    print "E[N(t)] = ", lambd / (mu - lambd)
    print "Average N length", navg / simtime

run_once()
