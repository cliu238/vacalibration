library(vacalibration)

# Test data
df <- data.frame(
    ID = c("d1", "d2"),
    cause = c("Birth asphyxia", "Neonatal sepsis"),
    stringsAsFactors = FALSE
)

print("Input data:")
print(df)

# Try cause_map
result <- tryCatch({
    cause_map(df = df, age_group = "neonate")
}, error = function(e) {
    print(paste("Error:", e$message))
    NULL
})

if (!is.null(result)) {
    print("Result:")
    print(result)
}