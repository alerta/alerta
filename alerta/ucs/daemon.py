
import UcsSdk
import time

def EventHandler(mce):
    print 'Received a New Event with ClassId: ' + str(mce.mo.classId)
    print "ChangeList: ", mce.changeList
    print "EventId: ", mce.eventId


def main():

    ucs = UcsSdk.UcsHandle()
    ucs.UcsHandle.Login(username='', password='')

    ucs.UcsHandle.AddEventHandler(classId='', callBack=EventHandler)

    while True:
        print '.',
        time.sleep(5)


    ucs.UcsHandle.Logout()

if __name__ == '__main__':
    main()


