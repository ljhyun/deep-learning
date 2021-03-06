import tensorflow as tf
from tensorflow.models.rnn import rnn_cell
from tensorflow.models.rnn import seq2seq


class JinRNN(object):
    def __init__(self, args):

        # define cell
        cell_fn = rnn_cell.BasicRNNCell
        cell = cell_fn(args.rnn_size)
        cell = rnn_cell.MultiRNNCell([cell] * args.num_layers)

        # define inputs and targets, initialize state
        self.inputs = tf.placeholder(tf.int32, [args.batch_size, args.seq_length])
        self.targets = tf.placeholder(tf.int32, [args.batch_size, args.seq_length])
        self.initial_state = cell.zero_state(args.batch_size, tf.float32)

        # prepare word embedding, reshape inputs
        with tf.name_scope("embedding"):
            W = tf.get_variable("W", [args.rnn_size, args.num_classes])
            b = tf.get_variable("b", [args.num_classes])
            with tf.device("/cpu:0"):
                embedding = tf.get_variable("word_embedding", [args.vocab_size, args.rnn_size])
                inputs = tf.split(1, args.seq_length, tf.nn.embedding_lookup(embedding, self.inputs))
                inputs = [tf.squeeze(input_, [1]) for input_ in inputs]

        # feed inputs into rnn
        with tf.name_scope("rnn"):
            outputs, states = seq2seq.rnn_decoder(inputs, self.initial_state, cell, loop_function=None, scope='rnnlm')
            self.output = tf.reshape(tf.concat(1, outputs), [-1, args.rnn_size])

        # Add dropout
        with tf.name_scope("dropout"):
            self.h_drop = tf.nn.dropout(self.output, args.dropout_keep_prob)

        # output layer
        with tf.name_scope("output"):
            self.logits = tf.nn.xw_plus_b(self.h_drop, W, b)
            self.probs = tf.nn.softmax(self.logits)
            self.predictions = tf.cast(tf.argmax(self.logits, 1), tf.int32)

        # accuracy
        with tf.name_scope("accuracy"):
            # calculate token-level accuracy
            self.reshaped_targets = tf.reshape(self.targets, [-1])
            correct_predictions = tf.equal(self.predictions, self.reshaped_targets)
            self.accuracy = tf.reduce_mean(tf.cast(correct_predictions, "float"))

            # calculate sentence-level accuracy
            self.predictions_sentence = tf.reshape(self.predictions, [-1, args.seq_length]) # batch_size * seq_length
            correct_predictions_sentence_tokens = tf.equal(self.predictions_sentence, self.targets)  # batch_size X seq_length
            multiply_mat = tf.constant(1, shape=[args.seq_length, 1])
            sentence_accuracy_mat = tf.matmul(tf.cast(correct_predictions_sentence_tokens, tf.int32), multiply_mat)  # batch_size X 1
            correct_predictions_sentence = \
                tf.equal(sentence_accuracy_mat, tf.constant(args.seq_length, shape=[args.batch_size, 1]))  # batch_size X 1
            self.accuracy_sentence = tf.reduce_mean(tf.cast(correct_predictions_sentence, "float"))

        # calculate loss
        with tf.name_scope("loss"):
            self.loss = seq2seq.sequence_loss_by_example(
                    [self.logits],  # TODO: should I use a list of 2D tensors ?
                    [self.reshaped_targets],  # TODO: correct ???
                    [tf.ones([args.batch_size * args.seq_length])],
                    args.num_classes)
            self.cost = tf.reduce_sum(self.loss) / args.batch_size / args.seq_length

        # train and update
        with tf.name_scope("update"):
            tvars = tf.trainable_variables()
            self.grads, _ = tf.clip_by_global_norm(tf.gradients(self.cost, tvars), args.grad_clip)  # TODO: correct ???
            optimizer = tf.train.AdamOptimizer(args.learning_rate)
            self.global_step = tf.Variable(0, name="global_step", trainable=False)
            self.train_op = optimizer.apply_gradients(zip(self.grads, tvars), global_step=self.global_step)