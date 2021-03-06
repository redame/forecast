#!/bin/env python
# coding:utf-8

# cnn calculation
# yesterday's nk,dj,dax,usdjpy,eurjpy,gold , today's nk225 output


import chainer
import chainer.links as L
import chainer.functions as F
import math
import random

import numpy as np
from chainer import optimizers
import time
import sys
import cPickle
import argparse
import MySQLdb
import matplotlib.pyplot as plt




random.seed(0)

IN_UNITS = 6  # nk,dj,dax,usdjpy,eurjpy,gold
OUT_UNITS = 1
DISPLAY_EPOCH = 100



class LSTM(chainer.Chain):
    def __init__(self, in_units, hidden_units, out_units):
        super(LSTM, self).__init__(
            l1=L.Linear(in_units, hidden_units),
            l2=L.LSTM(hidden_units, hidden_units),
            l3=L.LSTM(hidden_units, hidden_units),
            l4=L.LSTM(hidden_units, hidden_units),
            l5=L.LSTM(hidden_units, hidden_units),
            l6=L.Linear(hidden_units, out_units),
        )

    def __call__(self, x, t, train):
        h = self.l1(x)
        h = self.l2(h)
        h = self.l3(h)
        h = self.l4(h)
        h = self.l5(h)
        y = self.l6(h)
        if train:
            self.loss = F.mean_squared_error(y, t)
            return self.loss
        else:
            self.prediction = y
            return self.prediction

    def reset_state(self):
        self.l2.reset_state()
        self.l3.reset_state()
        self.l4.reset_state()
        self.l5.reset_state()


class DataMaker(object):
    def __init__(self):
        self.con=MySQLdb.connect(host="zcod4md.qr.com",db="live",user="root",passwd="")

    def make(self,xp,train):
        fromDate="2001-01-01"
        toDate="2011-12-31"
        if train==False :
            fromDate="2012-01-01"
            toDate="2015-12-31"

        cursor=self.con.cursor()
        cursor.execute("select i.cprice,d.cl,x.cl,e.price,g.price,u.price from indexHist i,idcStockDaily d,idcStockDaily x,otherHist e,otherHist g,otherHist u where i.date=x.date and  i.date=d.date and i.date=g.date and i.date=e.date and i.date=u.date and i.indexCode='101' and d.indexCode='I_DJI' and x.indexCode='DAX' and e.otherCode='EURO' and g.otherCode='GOLD' and u.otherCode='FEXCH' and i.date>=%s and i.date<=%s order by i.date asc",[fromDate,toDate])

        result = cursor.fetchall()
        cursor.close()
        items=xp.asarray(result, np.float32)
        return((items[1:]-items[:-1])/items[:-1])


    # http://qiita.com/hikobotch/items/d8ff5bebcf70083de089
    def make_mini_batch(self, data, mini_batch_size, length_of_sequence):
        sequences = xp.ndarray(( mini_batch_size, length_of_sequence,len(data[0])), dtype=np.float32)
        for i in range(mini_batch_size):
            index = random.randint(0, len(data) - length_of_sequence)
            sequences[i] = data[index:index + length_of_sequence]
        return sequences



def compute_loss(xp,model, sequences):
    loss = 0
    rows, cols ,in_unit= sequences.shape
    length_of_sequence = cols
    for i in range(cols - 1):
        x = chainer.Variable(
            xp.asarray(
                [sequences[j, i + 0 ] for j in range(rows)],
                dtype=np.float32
            )
        )
        t = chainer.Variable(
            xp.asarray(
                [sequences[j, i + 1, 0] for j in range(rows)],
                dtype=np.float32
            )[:, np.newaxis]
        )
        #x=chainer.Variable(sequences[:-1,i])
        #t=chainer.Variable(sequences[1:,i])
        loss += model(x, t, True)
    return loss


def training_main(xp, in_units, hidden_units, out_units,training_epochs,mini_batch_size,length_of_sequence):
    model_path="./35_model_"+str(hidden_units)+"_"+str(training_epochs)+"_"+str(length_of_sequence)+".bin"
    # make training data
    data_maker = DataMaker()
    train_data = data_maker.make(xp,True)

    # setup model
    model = LSTM(in_units, hidden_units, out_units)
    for param in model.params():
        data = param.data
        data[:] = np.random.uniform(-0.1, 0.1, data.shape)

    if args.gpu >= 0:
        model.to_gpu()

    # setup optimizer
    optimizer = optimizers.Adam()
    optimizer.setup(model)

    start = time.time()
    cur_start = start
    for epoch in range(training_epochs):
        sequences = data_maker.make_mini_batch(train_data, mini_batch_size=mini_batch_size, length_of_sequence=length_of_sequence)
        model.reset_state()
        model.zerograds()
        loss = compute_loss(xp,model, sequences)
        loss.backward()
        optimizer.update()

        if epoch % DISPLAY_EPOCH == 0:
            cur_end = time.time()
            # display loss
            print(
                "[{j}]training loss:\t{i}\t{k}[sec/epoch]".format(
                    j=epoch,
                    i=loss.data / (sequences.shape[1] - 1),
                    k=(cur_end - cur_start) / DISPLAY_EPOCH
                )
            )
            cur_start = time.time()
            sys.stdout.flush()

    end = time.time()

    # save model
    cPickle.dump(model, open(model_path, "wb"))

    print("{}[sec]".format(end - start))
    return (model_path)


def predict(xp,model, x_data):
    model.reset_state()
    x = chainer.Variable(xp.asarray([x_data], dtype=np.float32))
    dummy=x
    future = model(x,dummy, False)
    return future.data

def predict_main(xp, model_path):
    # load model
    model = cPickle.load(open(model_path))

    # make data
    data_maker = DataMaker()
    data = data_maker.make(xp,False)

    real_nk225=100
    predict_nk225=100
    print(",predict price="+str(predict_nk225)+",real price="+str(real_nk225))
    for i in range(0,len(data)-1):
        now_price=data[i]
        next_price=data[i+1]
        pprice=predict(xp, model,now_price)
        predict_nk225=predict_nk225*(1+pprice[0][0])
        real_nk225=real_nk225*(1+next_price[0])
        print(str(i)+",predict price="+str(predict_nk225)+",real price="+str(real_nk225))+",predict ratio="+str(pprice[0][0])+",real ratio="+str(next_price[0])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--gpu', '-g', default=-1, type=int, help='GPU ID (negative value indicates CPU)')
    parser.add_argument('--hidden','-d',default=100, type=int)
    parser.add_argument('--epochs','-e',default=20000, type=int)
    parser.add_argument('--size','-s',default=100, type=int)
    parser.add_argument('--sequence','-q',default=100, type=int)
    parser.add_argument('--model','-m',default="", type=str)

    args = parser.parse_args()
    if args.gpu >= 0:
        from chainer import optimizers, cuda
        cuda.check_cuda_available()
    xp = cuda.cupy if args.gpu >= 0 else np


    print ("gpu="+str(args.gpu)+",hidden="+str(args.hidden)+",epochs="+str(args.epochs)+",size="+str(args.size)+",sequence="+str(args.sequence)+",model="+str(args.model))
    hidden_units = args.hidden
    training_epochs = args.epochs
    mini_batch_size = args.size
    length_of_sequence = args.sequence
    if args.model == "":
        model_path=training_main(xp, IN_UNITS, hidden_units, OUT_UNITS,training_epochs,mini_batch_size,length_of_sequence)
    else:
        model_path=args.model

    predict_main(xp,model_path)


