#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum LexicalToken {
    NULL_TOKEN,
    RETURN,
    INT_LIT,
    SEMICOLON
};

typedef struct LexicalTokenNode {
    enum LexicalToken token;
    char lexeme[256];
} LexicalTokenNode;

int isAlpha(char c) {
    return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z');
}

int isAlphaNumeric(char c) {
    return isAlpha(c) || (c >= '0' && c <= '9');
}

int isWhitespace(char c){
    return c == ' ' || c == '\t' || c == '\n' || c == '\r';
}

int isNumber(char c){
    return c >= '0' && c <= '9';
}

void tokenToAsm(char buffer[256], LexicalTokenNode tokens[256], int nTokens) {
    strcpy(buffer, ".global _main\n_main:\n");
    int bufferIndex = 0;
    LexicalTokenNode token;
    for (int i = 0; i < nTokens; i++) {
        token = tokens[i];
        switch (token.token) {
            case RETURN:
                if (i + 2 < nTokens && tokens[i + 1].token == INT_LIT && tokens[i + 2].token == SEMICOLON) {
                    char code[256] = "    mov $0x2000001, %rax\n    mov $";
                    printf("Processing RETURN with INT_LIT: %s\n", tokens[i + 1].lexeme);
                    strcat(code,tokens[i + 1].lexeme);
                    strcat(code, ", %rdi\n");
                    strcat(code,"\n    syscall\n");
                    strcat(buffer,code);
                    i++;
                }
            case INT_LIT:
                break;
            case SEMICOLON:
                break;
            case NULL_TOKEN:
                break;
        
        }
    }
}

void tokenize(const char *input, LexicalTokenNode *tokens, int *nTokens) {
    char buffer[256]= {0};
    int bufferIndex = 0;
    int TokenIndex = 0;
    for (size_t i = 0; input[i] != '\0'; i++) {
        if (isAlpha(input[i])){
            printf("Processing character: %c\n", input[i]);
            while (isAlphaNumeric(input[i])) {
                printf("Processing lexical character: %c\n", input[i]);
                buffer[bufferIndex++] = input[i];
                i++;
            }
            buffer[bufferIndex] = '\0';
            bufferIndex = 0;
            i--;

            if (strcmp(buffer, "return") == 0) {
                printf("Token: RETURN\n");
                tokens[TokenIndex].token = RETURN;
                strcpy(tokens[TokenIndex].lexeme, buffer);
                TokenIndex++;
            }
            memset(buffer, 0, sizeof(buffer));
        }
        else if (isNumber(input[i])){
            printf("Processing character: %c\n", input[i]);
            while (isNumber(input[i])) {
                printf("Processing lexical character: %c\n", input[i]);
                buffer[bufferIndex++] = input[i];
                i++;
            }
            buffer[bufferIndex] = '\0';
            bufferIndex = 0;
            i--;

            printf("Token: INT_LIT, Lexeme: %s\n", buffer);
            tokens[TokenIndex].token = INT_LIT;
            strcpy(tokens[TokenIndex].lexeme, buffer);
            TokenIndex++;
            memset(buffer, 0, sizeof(buffer));
        }
        else if (input[i] == ';') {
            printf("Processing character: %c\n", input[i]);
            printf("Token: SEMICOLON\n");
            tokens[TokenIndex].token = SEMICOLON;
            strcpy(tokens[TokenIndex].lexeme, ";");
            TokenIndex++;
        }
        else if (isWhitespace(input[i])){
            continue;
        }
        else {
            printf("Unknown character: %c\n", input[i]);
        }

    }
    printf("Total tokens: %d\n", TokenIndex);
    *nTokens = TokenIndex;
}


int main(int argc, char const *argv[])
{
    if (argc != 2) {
        printf("Usage: %s <input.he>\n", argv[0]);
        return 1;
    }
    printf("%s\n",argv[1]);

    FILE *file = fopen(argv[1], "r");
    if (file == NULL) {
        perror("Error opening file");
        return 1;
    }

    char buffer[256];
    int nTokens = 0;
    LexicalTokenNode tokens[256] = {0};
    while (fgets(buffer, sizeof(buffer), file) != NULL) {
        tokenize(buffer, tokens, &nTokens);
    }

    fclose(file);

    char asmCode[256] = {0};
    tokenToAsm(asmCode,tokens, nTokens);
    printf("%s", asmCode);

    FILE *outputFile = fopen("output.asm", "w");
    if (outputFile == NULL) {
        perror("Error opening output file");
        return 1;
    }
    fprintf(outputFile, "%s", asmCode);
    fclose(outputFile);

    system("clang output.asm -o code -nostdlib -Wl,-e,_main -lSystem");
    
    return 0;
}
