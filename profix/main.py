from profix.commands import build_parser

# Main function to parse CLI arguments and dispatch commands
def main():
    parser = build_parser()

    # Parse arguments and call the appropriate function
    args = parser.parse_args()
    # Call the function associated with the chosen subcommand
    args.func(args)

if __name__ == "__main__":
    main()