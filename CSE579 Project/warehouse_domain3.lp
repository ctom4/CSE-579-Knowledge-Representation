#const maxT = 20.
time(0..maxT).
step(T) :- time(T), T < maxT.

robot(R) :- init(object(robot,R),_).
shelf(S) :- init(object(shelf,S),_).
product(PR) :- init(object(product,PR),_).
pstation(P) :- init(object(pickingStation,P),_).
order(O) :- init(object(order,O),_).
node(X,Y) :- init(object(node,_), value(at,pair(X,Y))).
highway(X,Y) :- init(object(highway,_), value(at,pair(X,Y))).

at(pstation,P,X,Y) :- init(object(pickingStation,P), value(at,pair(X,Y))).
order_station(O,P) :- init(object(order,O), value(pickingStation,P)).
order_line(O,PR,Q) :- init(object(order,O), value(line,pair(PR,Q))).
inv(PR,S,Q) :- init(object(product,PR), value(on,pair(S,Q))).

at(robot,R,X,Y,0) :- init(object(robot,R), value(at,pair(X,Y))).
onfloor(S,X,Y,0) :- init(object(shelf,S), value(at,pair(X,Y))).
carrying(R,S,0) :- robot(R), shelf(S), 1=0.

d(-1,0). d(1,0). d(0,-1). d(0,1). d(0,0).

1 { move(R,DX,DY,T) : d(DX,DY);
    pickup(R,S,T) : shelf(S);
    putdown(R,S,T) : shelf(S);
    deliver(R,S,O,P,T) : order(O), shelf(S), pstation(P)
} 1 :- robot(R), step(T).

pos_updated(R,T) :- move(R,_,_,T).
at(robot,R,NX,NY,T+1) :- move(R,DX,DY,T), at(robot,R,X,Y,T), NX=X+DX, NY=Y+DY, step(T).
at(robot,R,X,Y,T+1) :- at(robot,R,X,Y,T), not pos_updated(R,T), step(T).

carrying(R,S,T+1) :- pickup(R,S,T), step(T).
carrying(R,S,T+1) :- carrying(R,S,T), not putdown(R,S,T), step(T).

onfloor(S,X,Y,T+1) :- putdown(R,S,T), at(robot,R,X,Y,T), step(T).
onfloor(S,X,Y,T+1) :- onfloor(S,X,Y,T), not pickup(_,S,T), step(T).

at(shelf,S,X,Y,T) :- onfloor(S,X,Y,T), time(T).
at(shelf,S,X,Y,T) :- carrying(R,S,T), at(robot,R,X,Y,T), time(T).

:- move(R,DX,DY,T), at(robot,R,X,Y,T), NX = X+DX, NY = Y+DY, not node(NX,NY).
:- pickup(R,S,T), at(robot,R,X,Y,T), not onfloor(S,X,Y,T).
:- pickup(R,S,T), carrying(R,_,T).
:- putdown(R,S,T), not carrying(R,S,T).
:- deliver(R,S,O,P,T), at(robot,R,X,Y,T), not at(pstation,P,X,Y).
:- deliver(R,S,O,P,T), not carrying(R,S,T).
:- deliver(R,S,O,P,T), not order_station(O,P).

:- at(robot,R1,X,Y,T), at(robot,R2,X,Y,T), R1 < R2.
:- at(robot,R1,X1,Y1,T), at(robot,R2,X2,Y2,T), at(robot,R1,X2,Y2,T+1), at(robot,R2,X1,Y1,T+1), R1 < R2, step(T).
:- at(shelf,S1,X,Y,T), at(shelf,S2,X,Y,T), S1 < S2.
:- carrying(R,S1,T), carrying(R,S2,T), S1 < S2.
:- carrying(R1,S,T), carrying(R2,S,T), R1 < R2.
:- at(shelf,S,X,Y,T), highway(X,Y).

delivered_sum(O,PR,SUM,T) :- order_line(O,PR,_), step(T), SUM = #sum { Q,S : deliver(_,S,O,_,T), inv(PR,S,Q) }.
delivered_amount(O,PR,0,0) :- order_line(O,PR,_).
delivered_amount(O,PR,AMT_NEW,T+1) :- delivered_amount(O,PR,AMT_OLD,T), delivered_sum(O,PR,AMT_STEP,T), AMT_NEW = AMT_OLD + AMT_STEP, step(T).

needed(O,PR,T) :- order_line(O,PR,Q_REQ), delivered_amount(O,PR,Q_DEL,T), Q_DEL < Q_REQ, time(T).
need_from_shelf(O,S,T) :- needed(O,PR,T), inv(PR,S,_), step(T).
:- deliver(_,S,O,_,T), not need_from_shelf(O,S,T).

unsatisfied_line(T) :- time(T), order_line(O,PR,Q_REQ), delivered_amount(O,PR,Q_DEL,T), Q_DEL < Q_REQ.
goal_met(T) :- time(T), not unsatisfied_line(T).
:- not goal_met(maxT).

first_goal(T) :- goal_met(T), not goal_met(T-1), time(T), T > 0.
first_goal(0) :- goal_met(0).
#minimize { T@1 : first_goal(T) }.

#show move/4.
#show pickup/3.
#show putdown/3.
#show deliver/5.
#show first_goal/1.
