# OpenMP

OpenMP (Open Multi-Processing) is an API for shared-memory parallel programming in C, C++, and Fortran, standardized by the OpenMP Architecture Review Board since 1997. It uses compiler pragmas (`#pragma omp`) to annotate loops and parallel regions, letting the compiler and runtime handle thread creation, work distribution, and synchronization. This page covers the execution model, the major directives, the `task` model, and the offload support (OpenMP target).

## The Execution Model

OpenMP uses a fork-join model: a single thread starts the program (the "initial thread"). When the program hits a `#pragma omp parallel`, the runtime forks a team of N threads; the team executes the parallel region; on exit, the threads join back to the initial thread.

```c
#pragma omp parallel
{
    int tid = omp_get_thread_num();
    int nthreads = omp_get_num_threads();
    printf("Hello from thread %d of %d\n", tid, nthreads);
}
```

The number of threads is set via `OMP_NUM_THREADS` env var or `omp_set_num_threads()`. The default is the number of CPU cores.

## Worksharing Loops

The most common pattern: divide a loop's iterations across threads:

```c
#pragma omp parallel for
for (int i = 0; i < N; i++) {
    a[i] = b[i] + c[i];
}
```

The `parallel for` directive forks a thread team and divides the iterations. Each thread executes its chunk sequentially. After the loop, threads join.

The schedule determines how iterations are divided:
- `static`: equal-sized chunks, one per thread. Fast to schedule, but load imbalance if iterations have varying cost.
- `dynamic`: chunks of size N (default 1). Threads acquire the next chunk after finishing. Better for load imbalance, more overhead.
- `guided`: dynamic with chunks that shrink as the loop progresses. Good balance.
- `runtime`: choose at runtime via `OMP_SCHEDULE`.

```c
#pragma omp parallel for schedule(dynamic, 16) reduction(+:sum)
for (int i = 0; i < N; i++) {
    sum += a[i];
}
```

The `reduction(+:sum)` clause makes `sum` private to each thread, with the per-thread sums combined at the end.

## Synchronization Primitives

OpenMP provides:

- **barrier**: `#pragma omp barrier` — all threads wait until they all reach the barrier.
- **critical**: `#pragma omp critical` — only one thread executes the block at a time.
- **atomic**: `#pragma omp atomic` — atomic update of a single variable.
- **ordered**: `#pragma omp ordered` — execute a block in the loop's sequential order.
- **flush**: `#pragma omp flush` — memory barrier, ensuring visibility.

```c
int counter = 0;
#pragma omp parallel
{
    #pragma omp atomic
    counter++;
}
// counter is now == omp_get_max_threads()
```

The `atomic` is more efficient than `critical` for simple operations because it can use hardware atomic instructions. For complex blocks, `critical` is needed.

## Tasks

OpenMP 3.0 (2008) added tasks for irregular parallelism:

```c
#pragma omp parallel
{
    #pragma omp single
    {
        for (int i = 0; i < N; i++) {
            #pragma omp task firstprivate(i)
            process_node(i);
        }
    }
}
```

The `task` directive creates a unit of work that any thread in the team can execute. The `single` block ensures only one thread enqueues tasks; the other threads in the team execute them.

This is essential for tree traversal, graph algorithms, and any irregular workload where the work distribution can't be statically determined.

## Offload (OpenMP Target)

OpenMP 4.0 (2013) added directives for offloading to accelerators (GPUs, FPGAs):

```c
#pragma omp target
#pragma omp teams distribute parallel for
for (int i = 0; i < N; i++) {
    a[i] = b[i] + c[i];
}
```

The `target` directive offloads the code to the GPU; `teams distribute parallel for` distributes iterations across the GPU's thread blocks. This is the OpenMP equivalent of CUDA or HIP.

OpenMP target can also handle data movement:

```c
#pragma omp target data map(to: a[0:N], b[0:N]) map(from: c[0:N])
{
    #pragma omp target teams distribute parallel for
    for (int i = 0; i < N; i++) {
        c[i] = a[i] + b[i];
    }
}
```

The `map` clauses handle the HBM↔host memory transfers.

## Production Use

OpenMP is widely used in scientific computing:
- **LAMMPS** (molecular dynamics): OpenMP for CPU parallelism, CUDA for GPU.
- **Quantum ESPRESSO** (DFT): OpenMP for CPU parallelism.
- **GROMACS** (molecular dynamics): hybrid MPI+OpenMP for cluster parallelism.

The hybrid MPI+OpenMP model is the standard for HPC: MPI across nodes, OpenMP within nodes. This combines MPI's distributed-memory scaling with OpenMP's shared-memory efficiency.

## Performance Considerations

1. **False sharing**: threads writing to adjacent array elements invalidate each other's cache lines. Pad arrays or use padding to avoid.

2. **Load imbalance**: if one thread's chunk takes 10× longer, the others wait. Use `schedule(dynamic)` for irregular workloads.

3. **NUMA effects**: a thread on CPU 0 accessing memory on NUMA node 1 is slow. Use `proc_bind(close)` to keep threads near their data.

4. **Memory allocation**: malloc inside a parallel region serializes threads (the heap lock). Pre-allocate before the parallel region.

## Common Pitfalls

1. **Forgetting that `private` variables are uninitialized.** A `private` clause gives each thread its own copy, but the copy is uninitialized. Use `firstprivate` to initialize from the master thread's value.

2. **Race conditions in reductions.** A naive `sum += a[i]` in a parallel for has a race. Always use the `reduction` clause.

3. **Trusting the order of execution.** OpenMP doesn't guarantee execution order between threads. Use `ordered` if you need sequential semantics.

4. **Forgetting the barrier at the end of a `for`.** A parallel for has an implicit barrier; if you want to skip it, use `nowait`. But the next loop may not see the writes from this one.

5. **Forgetting that nested parallelism needs `OMP_NESTED=true`.** By default, nested `parallel` directives are serialized.

6. **Treating OpenMP target as a drop-in for CUDA.** The performance is usually worse; OpenMP target is good for portable code but loses to CUDA for performance-critical kernels.

## References

- [OpenMP specification](https://www.openmp.org/specifications/)
- [OpenMP API examples](https://www.openmp.org/wp-content/uploads/OpenMP-4.5-1115-CPP-web.pdf)
- [OpenMP Application Programming Interface Examples](https://github.com/OpenMP/Examples)
- [LLVM OpenMP runtime](https://github.com/llvm/llvm-project/tree/main/openmp)
- [Intel oneAPI OpenMP documentation](https://www.intel.com/content/www/us/en/develop/documentation/oneapi-mpi-developer-guide-linux/top.html)
- [OpenMP on GPUs (target directives)](https://www.openmp.org/wp-content/uploads/OpenMP-4.5-1115-CPP-web.pdf)
- Mattson & Meadows, "[A 'Hands-on' Introduction to OpenMP](https://www.openmp.org/wp-content/uploads/Introduction-to-OpenMP-2019.pdf)" (2019)
- [LWN: OpenMP in modern C++ (2019)](https://lwn.net/Articles/797031/)
