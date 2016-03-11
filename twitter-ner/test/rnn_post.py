from itertools import islice

filename = "./codecount122.txt"

#Converts string representation of list to list
def convToList(string):
    return map(int,string.replace('[','').replace(']','').split())

cnt = 0
total = 0
with open(filename,'r') as f:
    try:
        while True:
            #Batch in 11 lines, first 4 are predicted, next 4 is actual
            line = islice(f,0,11)
            predicted = convToList(next(line)+next(line)+next(line)+next(line))
            actual = convToList(next(line)+next(line)+next(line)+next(line))
            #Last three are batch # and two newlines which is ignored
            for i in range(3):
                line.next()
            #Post processing step
            if predicted[0] == 2:
                predicted[0] = 1
            for code in range(len(predicted)-1):
                if predicted[code] == 0 and predicted[code+1] == 2:
                    predicted[code] = 1
            
            if predicted == actual:
                cnt+=1
            
            total+=1
            
    except StopIteration:
        print cnt,total
