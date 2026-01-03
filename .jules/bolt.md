## 2024-05-22 - [Git Performance Surprises]
**Learning:** Git `for-each-ref` is surprisingly fast, even with 2000+ branches (approx 3ms per call). Optimizing by filtering specific branches via arguments vs filtering in Python yields negligible performance gains for typical workloads, making the added code complexity unjustified.
**Action:** When optimizing git commands, always benchmark with large datasets first. Focus on reducing subprocess creation count rather than optimizing fast git internal commands.
