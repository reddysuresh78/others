import subprocess
import time

gc_cmd_line=r"E:\ProgramFiles\Java\jdk-9.0.4\bin\java -Xlog:gc*  -cp F:\eclipse-workspace2020\gctest\target\gctest-0.0.1-SNAPSHOT.jar gctest.GCCreator 10000000"
log_writer_cmd_line=r"E:\ProgramFiles\Java\jdk-9.0.4\bin\java -cp F:\eclipse-workspace2020\logwriter\target\logwriter-0.0.1-SNAPSHOT.jar logwriter.LogWriter e:\gc.txt"

gc_commands = gc_cmd_line.split()
log_writer_commands = log_writer_cmd_line.split()

print(f"Starting Log Writer process - {log_writer_commands}")
p2 = subprocess.Popen(log_writer_commands, stdin=subprocess.PIPE)
time.sleep(2)
print(f"Starting GC Writer process - {gc_commands}")
p1 = subprocess.Popen(gc_commands, stdout=p2.stdin, stderr=subprocess.PIPE)

while p1.poll() is None:
    time.sleep(5)
    print("Waiting for process to finish")

p2.terminate()
print("Finished both processes")